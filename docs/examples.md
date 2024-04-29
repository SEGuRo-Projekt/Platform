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

### Job Worker

```{note}
**ToDo:** This section still needs to be written.
```

### Streaming Worker

```{note}
**ToDo:** This section still needs to be written.
```
