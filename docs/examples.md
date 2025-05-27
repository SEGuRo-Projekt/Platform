# Examples

We provide a couple of examples of _application services_ and , Jupyter Notebooks and configuration files for getting started quickly:

## Configuration Files

Upon startup of the platform, we automatically copy all files within the [`/store`](https://github.com/SEGuRo-Projekt/Platform/tree/main/store) folder of the GitHub repo to the data store.

These files include general configuration files, like scheduler specifications, access control lists and Jupyter Notebooks.

## Jupyter Notebooks

We provide simple [Jupyter Notebooks](https://jupyter-notebook.readthedocs.io/en/stable/notebook.html) inside [`/store/notebooks`](https://github.com/SEGuRo-Projekt/Platform/tree/main/store/notebooks) which are evaluated by the [_notebook executor_](architecture.md#Notebook Executor).

The evaluation of these notebooks is usually triggered by the [_scheduler_](architecture.md#Scheduler) whenever new sample data has been added to the sore by the [_sample recorder_](architecture.md#Sample Recorder) or at regular intervals (e.g. daily).

## Application Services

Application services are the primary approach to implement business logic in the platform.
They allow you to integrate third-party tools.

Two examples for such services are shipped as standalone Docker images in [`images/examples`](https://github.com/SEGuRo-Projekt/Platform/tree/main/images/examples).

### Service Deployment

To deploy your application services, follow these steps:

1. **Package Your Application as a Docker Container**
   If your application uses parts of the SEGuRo Platform toolchain (e.g., the broker or store), it is recommended to use the `seguro-platform` base image. Below is an example `Dockerfile`:

   ```Dockerfile
   # Dockerfile
   FROM registry.localhost/seguro:latest

   COPY my_service.py /platform/seguro
   WORKDIR /platform/seguro
   ```

2. **Login to the Platform Docker Registry**
   Use the admin credentials configured in the environment file to log in to the platform's Docker registry. By default, the credentials are `admin / s3gur0herne` (see [Configuration](configuration.md) and [Access](access.md) for more details).

   ```shell
   docker login registry.localhost
   ```

3. **Push Your Image to the Docker Registry**
   Push your Docker image to the registry using the following command:

   ```shell
   docker push registry.localhost/my-image:my-tag
   ```

4. **Upload a Job Configuration File**
   To start your service on the platform using the scheduler, upload a YAML job specification describing the scheduling process to the object store at `seguro/config/jobs/`. This can be done via the [store UI frontend](https://ui.store.localhost). Below is a minimal example configuration. For more details, refer to the [job.yaml.example](https://github.com/SEGuRo-Projekt/Platform/blob/main/store/config/jobs/job.yaml.example).

   ```yaml
   # my-job.yaml
   # Example configuration for a job

   container:
     image: registry.localhost/my-image:my-tag

     environment:
       MY_VAR: "foo"

     command: ["python my_service.py"]
   ```

   ```{note}
   Since no explicit trigger is defined, the job will start immediately after uploading the file and after each restart of the scheduler service.
   ```

### Job Worker

The [example job worker](../images/examples/job-worker/job_worker/main.py) is a script that processes store data triggered by the creation of specific store objects. When triggered, it retrieves a data frame from the created object, doubles its values, and saves the processed frame to a new location in the store (`measurements_processed`).

For accesing the store, it uses the [store helper class](https://github.com/SEGuRo-Projekt/Platform/blob/main/seguro/common/store.py).

**Dockerfile:**
```{literalinclude} ../images/examples/job-worker/Dockerfile
```

**Job Specification:**
```{literalinclude} ../store/config/jobs/example-job-worker.yaml
```

### Streaming Worker

The [example streaming worker](../images/examples/streaming-worker/streaming_worker/main.py) is a script that processes all incoming samples on a given topic (`data/measurements/mp1`) at the broker. When triggered, it scales the values based on their index within the sample, and publishes the resulting scaled samples to another topic (`data/measurements/processed_by_streaming_worker/mp1`).

For accessing the broker, it uses the [broker helper class]((https://github.com/SEGuRo-Projekt/Platform/blob/main/seguro/common/broker.py))

**Dockerfile:**
```{literalinclude} ../images/examples/streaming-worker/Dockerfile
```

**Job Specification:**
```{literalinclude} ../store/config/jobs/examples-streaming-worker.yaml
```
