from airflow.models import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

import pendulum
import datetime

with DAG(
    dag_id = "exercise3",
    start_date = pendulum.today('UTC').add(days=-3),
    description = "Exercise 3",
    schedule = "@daily",
) as dag:

    print_task_dag = BashOperator(
        task_id="print_task_dag",
        bash_command="echo '{{ task }} is running in the {{ dag }} pipeline'",
        dag=dag,
    )

    def _print_exec_date(**context):
        execution_date = context["execution_date"]
        print(f"This script was executed at {execution_date}")
        three_days_later = context["execution_date"] + datetime.timedelta(days=3)
        print(f"Three days after execution is {three_days_later}")
        ds_date = context["ds"]
        print(f"The script run date is {ds_date}")
    
    print_dates = PythonOperator(
        task_id="print_dates",
        python_callable=_print_exec_date,
        provide_context=True,
        dag=dag,
    )

    print_task_dag >> print_dates
