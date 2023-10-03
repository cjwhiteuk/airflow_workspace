from airflow.models import DAG
from airflow.operators.empty import EmptyOperator
import pendulum

with DAG(
    dag_id = "rocket_launch",
    start_date = pendulum.today('UTC'),
    description = "To the moon!",
    schedule = "@daily",
) as dag:

    procure_rocket_material = EmptyOperator(task_id = "procure_rocket_material", dag=dag)
    procure_fuel = EmptyOperator(task_id = "procure_fuel", dag=dag)
    build_tasks = [EmptyOperator(task_id = f"build_stage_{i}", dag=dag) for i in range(1,4,1)]
    launch = EmptyOperator(task_id = "launch", dag=dag)

    procure_rocket_material >> build_tasks
    procure_fuel >> build_tasks[2]
    build_tasks >> launch