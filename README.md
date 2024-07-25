# Ticket Batch Process

A database table/model "Ticket" has 1 million rows. The table has a "token" column that holds a random unique UUID value for each row, determined by Django/Python logic at the time of creation.

Due to a data leak, the candidate should write a Django management command to iterate over every Ticket record to regenerate the unique UUID value.

The command should inform the user of progress as the script runs and estimate the remaining time.

The script should also be sensitive to the potentially limited amount of server memory, avoiding loading the full dataset into memory all at once, and should show an understanding of Django ORM memory usage and query execution.

Finally, the script should ensure that if it is interrupted, it saves progress and restarts near the point of interruption so that it does not need to process the entire table from the start.

## Environment Setup

1. Build and start Docker Compose services
    ```bash
    docker-compose up -d --build
    ```

2. Access the `app` container
    ```bash
    docker-compose exec app bash
    ```

3. Migrate the database
    ```bash
    python manage.py migrate
    ```

4. Add sample data to the database
    ```bash
    python manage.py ticket --init --size 50000
    ```

## Run the command

- Run the command to regenerate a token for each ticket record
    ```bash
    python manage.py ticket --process-token
    ```

- The command shows the progress of the script as well as the estimated time remaining
    ```bash
    completed:  2.30 % (1150 of 50000) | remaining time:   31 second(s)
    ```

- If the command is interrupted for any reason, it can save progress and, when restarted, will continue from near the point of interruption
    ```bash
    completed: 30.30 % (14800 of 48850) | remaining time:   21 second(s)
    ```

## Solution

We assume that the Ticket table has the ID field as the primary key, which is an auto-increment number.

We use a table `batchprogress` to keep track of the state of the batch process and the last ID of the record successfully processed.

## Implementation

There are two main management commands: `init` and `process-token`, located at `src/app/management/commands/ticket.py`

### 1. The `init` command

The `init` command will clean up the data and regenerate sample data with the total number of records specified by the `size` argument (default: 1000).

### 2. The `process-token` command

We build a queryset that filters and orders the records based on the primary key (which by default has a B-Tree index).

We calculate the total records that need to be processed first. After that, we loop until we process all the records.
```python
total = Ticket.objects.filter(pk__gt=last_pk).count()

...

offset = 0
while offset < total:
    ...

    last_pk = self.batch_process(last_pk)
    offset += self.BULK_SIZE
```

For each iteration of the loop, we limit the results by `BULK_SIZE` (default: 50)

```python
chunk = iter(Ticket.objects.filter(pk__gt=pk).order_by("pk")[:self.BULK_SIZE])
```
The `chunk` here is also an iterator, so it won't load into memory until we access it.

For each chunk of data, we update the batch state by saving the last ID of the record processed.
We also use `bulk_update` for tickets to reduce the number of query operations.
```python
try:
    Ticket.objects.bulk_update(bulk, ["token"])
    self.update_batch_state({'last_value': last_pk}, None, None)
except:
    self.update_batch_state({'last_value': pk}, None, None)
    return pk
```

The progress and estimated time remaining are calculated based on the total records that need to be processed and the number of records already processed successfully in the time taken so far
```python
percentage = offset * 100.0 / total

took = time.time() - start_time
return {
    'percentage': percentage,
    'remaining_time': "%0.0f" % ((total - offset) / offset * took) if offset > 0 else "-"
}
```