import time

from django.core.management.base import BaseCommand
from django.db import connection

from app.models import BatchProgress, Ticket


class Command(BaseCommand):
    BULK_SIZE = 50
    TICKET_BATCH_PROGRESS_KEY = "TICKET_BATCH_PROGRESS_KEY"

    def add_arguments(self, parser):
        parser.add_argument(
            "-i",
            "--init",
            action="store_true",
            help="Initialize sample data for the Ticket table",
        )

        parser.add_argument(
            "-p",
            "--process-token",
            action="store_true",
            help="Generate token for each Ticket record",
        )

        parser.add_argument(
            "-s",
            "--size",
            default=1000,
            help="Sample data size",
        )

    def init(self, size):
        with connection.cursor() as cursor:
             cursor.execute('delete from app_ticket;')
             cursor.execute('delete from app_batchprogress;')
             
        BatchProgress(batch_key=self.TICKET_BATCH_PROGRESS_KEY, last_value=0, state=BatchProgress.BATCH_PROGESS_STATE_INIT).save()

        inserted = 0
        while inserted < size:
            items = [Ticket() for _ in range(self.BULK_SIZE)]
            Ticket.objects.bulk_create(items)

            inserted += self.BULK_SIZE
            self.stdout.write("inserted: {}".format(inserted))

    def update_batch_state(self, data, state, error):
        batch = BatchProgress.objects.filter(batch_key=self.TICKET_BATCH_PROGRESS_KEY).first()
        batch.state = state or batch.state

        if data:
            batch.last_value = data['last_value']

        if state == BatchProgress.BATCH_PROGESS_STATE_ERROR:
            batch.error = error
        
        batch.save()

    def get_progress_info(self, start_time, offset, total):
        percentage = offset * 100.0 / total

        took = time.time() - start_time
        return {
            'percentage': percentage,
            'remaining_time': "%0.0f" % ((total - offset) / offset * took) if offset > 0 else "-"
        }

    def batch_process(self, pk):
        chunk = iter(Ticket.objects.filter(pk__gt=pk).order_by("pk")[:self.BULK_SIZE])

        last_pk = None
        bulk = []
        for item in chunk:
            item.generate_token()
            bulk.append(item)

            last_pk = item.id

        try:
            Ticket.objects.bulk_update(bulk, ["token"])
            self.update_batch_state({'last_value': last_pk}, None, None)

        except:
            self.update_batch_state({'last_value': pk}, None, None)
            return pk

        return last_pk

    def process_token(self):
        batch = BatchProgress.objects.get(batch_key=self.TICKET_BATCH_PROGRESS_KEY)
        # if batch.state == BatchProgress.BATCH_PROGESS_STATE_RUNNING:
        #     self.stderr.write("Process is running...")
        #     return
        
        try:
            self.update_batch_state(None, BatchProgress.BATCH_PROGESS_STATE_RUNNING, None)

            last_pk = batch.last_value

            total = Ticket.objects.filter(pk__gt=last_pk).count()

            start_time = time.time()

            offset = 0
            while offset < total:
                self.stdout.flush()

                progress_info = self.get_progress_info(start_time, offset, total)
                self.stdout.write("  completed: %5.2f %% (%d of %d) | remaining time: %4s second(s)" % (progress_info['percentage'], offset, total, progress_info['remaining_time']), ending='\r')

                last_pk = self.batch_process(last_pk)
                offset += self.BULK_SIZE

            self.update_batch_state({'last_value': last_pk}, BatchProgress.BATCH_PROGESS_STATE_FINISHED, None)

            self.stdout.flush()
            self.stdout.write("  completed: %5d record(s) | took: %0.0f second(s)\n" % (total, time.time() - start_time), ending="")

        except Exception as e:
            self.update_batch_state(None, BatchProgress.BATCH_PROGESS_STATE_ERROR, str(e))
        
    def handle(self, *args, **options):
        if options.get("init"):
            try:
                size = int(options.get("size"))
            except:
                size = 1000

            self.init(size)

        elif options.get("process_token"):
            self.process_token()
        
        else:
            self.stdout.write("- Init data:\n    python manage.py ticket --init --size 500")
            self.stdout.write("- Process token:\n    python manage.py ticket --process-token")
