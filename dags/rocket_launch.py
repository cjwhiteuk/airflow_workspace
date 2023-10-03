from airflow.models import DAG
from airflow.operators.empty import EmptyOperator
import pendulum
from airflow.contrib.sensors.ftp_sensor import FTPSensor
from airflow.providers.http.sensors.http import HttpSensor
from airflow.operators.python import PythonOperator
from airflow.hooks.base_hook import BaseHook
from airflow.operators.http_operator import SimpleHttpOperator
from airflow.operators.python import BranchPythonOperator
from airflow.exceptions import AirflowSkipException
from airflow.operators.python import ShortCircuitOperator
from airflow.providers.google.cloud.transfers.local_to_gcs import LocalFilesystemToGCSOperator

import json

with DAG(
    dag_id = "rocket_launch2",
    start_date = pendulum.today('UTC').add(days=-10),
    description = "To the moon!",
    schedule = "@daily",
) as dag:

    wait_for_data = HttpSensor(
        task_id = "wait_for_data",
        endpoint = "", 
        http_conn_id='thespacedevs_dev')

    task_get_op = SimpleHttpOperator(
        task_id="task_get_op",
        method="GET",
        http_conn_id='thespacedevs_dev',
        endpoint="",
        data={"net__gte": "{{ ds }}T00:00:00Z", "net__lt": "{{ next_ds }}T00:00:00Z"},
        log_response=True,
        dag=dag,
    )

    def _check_count(task_instance, **context):
        result_by_key = task_instance.xcom_pull(task_ids="task_get_op", key="return_value")
        result_dict = json.loads(result_by_key)
        count_not_zero = (result_dict["count"] > 0)

        if not count_not_zero:
            raise AirflowSkipException(f"No launches on {context['ds']}")
        #return count_not_zero

    check_launches = PythonOperator(
        task_id="check_launches", 
        python_callable=_check_count, 
        provide_context=True,
        dag=dag
    )

    def _extract_relevant_data(x: dict):
        return {
            "id": x.get("id"),
            "name": x.get("name"),
            "status": x.get("status").get("abbrev"),
            "country_code": x.get("pad").get("country_code"),
            "service_provider_name": x.get("launch_service_provider").get("name"),
            "service_provider_type": x.get("launch_service_provider").get("type")
        }

    def _preprocess_data(task_instance, **context):
        response = task_instance.xcom_pull(task_ids="task_get_op")
        response_dict = json.loads(response)
        response_results = response_dict["results"]
        df_results = pd.DataFrame([_extract_relevant_data(i) for i in response_results])
        df_results.to_parquet(path=f"/tmp/{context['ds']}.parquet")

    preprocess_data = PythonOperator(
        task_id="preprocess_data",
        python_callable=_preprocess_data,
        provide_context=True,
        dag=dag
    )

    create_dataset = BigQueryCreateEmptyDatasetOperator(task_id="create_dataset", dataset_id="aflow-training-rabo-2023-10-02.chris")

    create_table = BigQueryCreateEmptyTableOperator(
        task_id="create_table",
        dataset_id="aflow-training-rabo-2023-10-02.chris",
        table_id="aflow-training-rabo-2023-10-02.chris.rockets",
        schema_fields=[
            {"name": "id", "type": "STRING", "mode": "REQUIRED"},
            {"name": "name", "type": "STRING", "mode": "NULLABLE"},
            {"name": "status", "type": "STRING", "mode": "NULLABLE"},
            {"name": "country_code", "type": "STRING", "mode": "NULLABLE"},
            {"name": "service_provider_name", "type": "STRING", "mode": "NULLABLE"},
            {"name": "service_provider_type", "type": "STRING", "mode": "NULLABLE"},
        ],
    )

    upload_file = LocalFilesystemToGCSOperator(
        task_id="upload_file",
        src="/tmp/{{ ds }}.parquet",
        dst="agustinir/launches/{{ ds }}.parquet",
        bucket="aflow-training-rabo-2023-10-02",
        gcp_conn_id='GoogleBigQuery',
    )
    
    wait_for_data >> task_get_op
    task_get_op >> check_launches
    check_launches >> preprocess_data
    preprocess_data >> create_dataset
    create_dataset >> [create_table, upload_file]
    
