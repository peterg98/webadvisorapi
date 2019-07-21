from django.core.management.base import BaseCommand, CommandError
from ...scripts import request
import time

class Command(BaseCommand):
    help = 'Runs requests to seed the API database. Accepts an int argument ' + \
    'which will be the time delay between each request.'

    def add_arguments(self, parser):
        parser.add_argument('minutes', type=int)

    def handle(self, *args, **options):
        while True:
            try:
                request.main()
            except:
                pass
            time.sleep(options['minutes'] * 60)
        