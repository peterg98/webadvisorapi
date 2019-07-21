import sys
import os
import django
import asyncio
from pyppeteer import launch
import re
from pyppeteer.errors import NetworkError

PAGE_LIMIT_REGEX = r'Page (\d+) of (\d+)'
COURSE_SECTION_REGEX = r'([a-zA-Z0-9]+-[a-zA-Z0-9]+)-([a-zA-Z0-9]+)'

BASE_WEBADVISOR_URL = 'https://advisor.uog.edu/WebAdvisor/WebAdvisor'
SECTION_DETAIL_URL_REGEX = r"'(.*?)'"

STATUS_PATTERN_ID = '#LIST_VAR1_'
SECTION_TITLE_ID = '#SEC_SHORT_TITLE_'
LOCATION_ID = '#SEC_LOCATION_'
FACULTY_ID = '#SEC_FACULTY_INFO_'
CAPACITY_ID = '#LIST_VAR5_'
CREDITS_ID = '#SEC_MIN_CRED_'
ACADEMIC_LEVEL_ID = '#SEC_ACAD_LEVEL_'

DESCRIPTION_ID = '#VAR3'
MEETING_INFO_ID = '#LIST_VAR12_1'
REQUISITE_COURSES_ID = '#VAR_LIST1_1'
PHONE_ID = '#LIST_VAR8_1'
EXTENSION_ID = '#LIST_VAR9_1'
EMAIL_ID = '#LIST_VAR10_1'
INSTRUCTIONAL_METHOD_ID = '#LIST_VAR11_1'

PATTERN_IDS = [STATUS_PATTERN_ID, SECTION_TITLE_ID, LOCATION_ID, 
             FACULTY_ID, CAPACITY_ID, CREDITS_ID, ACADEMIC_LEVEL_ID]
    
DETAIL_PATTERNS = [DESCRIPTION_ID, MEETING_INFO_ID, REQUISITE_COURSES_ID, PHONE_ID, EXTENSION_ID,
                EMAIL_ID, INSTRUCTIONAL_METHOD_ID]

os.environ['DJANGO_SETTINGS_MODULE'] = 'webadvisorapi.settings'
django.setup()

from src import models

class CourseScraper:
    def __init__(self, term):
        self.term = term
        self.primary_cookies = None
        
    async def queryCourses(self):
        #set headless=True when in production
        self.browser = await launch(headless=True, args=['--disable-dev-shm-usage', '--no-sandbox', '--disable-setuid-sandbox']) #Chromium will run out of memory when doing memory-intensive functions, so disable the limit
        #Incognito might not be needed when disabling browser cache
        self.context = await self.browser.createIncognitoBrowserContext()  
        self.page = await self.context.newPage()
        await self.page.setCacheEnabled(False)
        
        await self.page.goto(
            'https://advisor.uog.edu/WebAdvisor/WebAdvisor?CONSTITUENCY=WBST&type=P&pid=ST-WESTS12A&TOKENIDX=', 
            waitUntil=['networkidle0', 'domcontentloaded', 'load']
            )

        async def isTermAvailable():
            options = await self.page.querySelectorAll('#VAR1 option')
            options = [await (await option.getProperty('value')).jsonValue() for option in options]
            
            return False if self.term not in options else True
        
        if not await isTermAvailable():
            await self.page.close()
            await self.browser.close()
            return
        
        await self.page.select('#VAR1', self.term)
        await self.page.select('#VAR7', '05:00')
        await self.page.select('#VAR8', '22:00')
        await asyncio.gather(
            self.page.waitForNavigation(waituntil=['networkidle0', 'domcontentloaded', 'load'], ignoreHTTPSErrors=True),
            self.page.click('.shortButton')
        )
        try:
            num_pages = await (await (await self.page.querySelector('table[summary="Paged Table Navigation Area"]')).getProperty('innerText')).jsonValue()
        except AttributeError:
            await self.page.close()
            await self.browser.close()
            return
        pages_begin, pages_end = map(lambda x: int(x), re.match(PAGE_LIMIT_REGEX, num_pages.strip()).groups())
        self.termObj, isTermCreated = models.Term.objects.get_or_create(term_code=self.term.replace("/", ""))
        
        while pages_begin <= pages_end:
            #IMPORTANT: The first cookies we see when entering the list of courses must be used, and all other cookies discarded.
            #If the cookies we store is different than those of the first, then we cannot access the next pointer to the next 
            #page of courses. 
            print("Reading page " + str(pages_begin))
            if not self.primary_cookies:
                self.primary_cookies = await self.page.cookies()
            await self.parsePage()
            
            await asyncio.gather(
                self.page.waitForNavigation(waituntil=['domcontentloaded', 'networkidle0', 'load']),
                self.page.click('input[value="NEXT"]')
            )
            
            pages_begin += 1
            
            await self.clearAndSetCookies()
        await self.page.close()
        await self.browser.close()
    
    async def parsePage(self):
        for i in range(1, 21):
            print("Reading course " + str(i))
            #Same here, delete all existing cookies and set it to our first ones
            await self.clearAndSetCookies()
            
            course_status = await self.page.querySelector(STATUS_PATTERN_ID + str(i))
            if course_status == None:
                return
            else:
                status, section_name_and_title, location, faculty, \
                max_capacity, credits_, academic_level = [await self.querySelectorHelper(i, pattern) for pattern in PATTERN_IDS]
                
                section_name_and_title = section_name_and_title.split(' ')
                name, title = section_name_and_title[0], ' '.join(section_name_and_title[2:])
                #Get the onclick attribute of an element; there seems to be no other way to get this attribute with only pyppeteer
                detail_url_segment = await self.page.evaluate('''() => document.querySelector('%s').getAttribute('onclick')''' % (SECTION_TITLE_ID + str(i)))
                detail_url_segment = re.findall(SECTION_DETAIL_URL_REGEX, detail_url_segment)[0]

                #some courses have a null max_capacity value, so catch the error
                try:
                    available, capacity = map(lambda c: int(c), max_capacity.strip().split('/'))
                except ValueError:
                    available, capacity = 0, 0
                course, section = re.match(COURSE_SECTION_REGEX, name).groups()
                credits_ = int(float(credits_))

                description, meeting_info, requisite_courses, phone, extension, \
                email, inst_method = await self.detail_parser(detail_url_segment)               

                courseObj, isCourseCreated = models.Course.objects.update_or_create(
                    course_code=course,
                    defaults={
                        'term': self.termObj,
                        'title': title,
                        'credit_points': credits_,
                        'academic_level': academic_level
                    }
                )

                sectionObj, isSectionCreated = models.Section.objects.update_or_create(
                    section_number=name,
                    defaults={
                        'parent_course': courseObj,
                        'description': description,
                        'phone': phone,
                        'extension': extension,
                        'email': email,
                        'requisite_courses': requisite_courses,
                        'instructional_method': inst_method,
                        'location': location,
                        'meeting_info': meeting_info,
                        'faculty': faculty,
                        'available': available,
                        'max_capacity': capacity,
                        'status': status
                    }
                )

    async def detail_parser(self, url_suffix):
        detailPage = await self.context.newPage()
        await detailPage.goto(BASE_WEBADVISOR_URL + url_suffix, waitUntil=['networkidle0', 'domcontentloaded', 'load'])
        response = [await self.detailquerySelectorHelper(detailPage, pattern) for pattern in DETAIL_PATTERNS]
        await detailPage.close()
        return response
        
    async def querySelectorHelper(self, idx, idPattern):
        #do not await selector, seems to have issues
        element = await self.page.querySelector(idPattern + str(idx))
        innerText = await (await element.getProperty('textContent')).jsonValue()
        return innerText

    async def detailquerySelectorHelper(self, context, idPattern):
        return await (await (await context.querySelector(idPattern)).getProperty('innerText')).jsonValue()

    async def clearAndSetCookies(self):
        for cookie in await self.page.cookies():
            await self.page.deleteCookie(cookie)
        for p in self.primary_cookies:
            await self.page.setCookie(p)

def create_term_codes():
    import datetime
    suffixes = ['SP', 'XA', 'XB', 'XC', 'X1', 'FA', 'FI']
    current_year = str(datetime.date.today().year)[2:]
    return map(lambda prefix: '/'.join([current_year, prefix]), suffixes)

def main():
    for term in create_term_codes():
        print("Starting with term " + term)
        course_scraper = CourseScraper(term)
        asyncio.get_event_loop().run_until_complete(course_scraper.queryCourses())