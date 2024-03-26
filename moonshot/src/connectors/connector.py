from __future__ import annotations

import asyncio
import time
from abc import abstractmethod
from asyncio import sleep
from functools import wraps
from pathlib import Path
from typing import Callable, Union

from moonshot.src.benchmarking.prompt_arguments import PromptArguments
from moonshot.src.connectors.connector_endpoint_arguments import (
    ConnectorEndpointArguments,
)
from moonshot.src.storage.storage_manager import StorageManager
from moonshot.src.utils.import_modules import get_instance


def perform_retry(func):
    """
    A decorator to perform retries on a function.

    This decorator wraps a function to enable retrying the function call
    if it fails. The number of retries and the delay between retries
    are determined by the `retries_times` and `allow_retries`
    attributes of the class instance.

    Parameters:
    - func (Callable): The function to be wrapped and retried.

    Returns:
    - Callable: A wrapper function that includes retry logic.
    """

    async def wrapper(self, *args, **kwargs):
        if self.allow_retries:
            retry_count = 0
            base_delay = 1
            while retry_count <= self.retries_times:
                # Perform the request
                try:
                    return await func(self, *args, **kwargs)
                except Exception as exc:
                    print(f"Operation failed. {str(exc)} - Retrying...")

                # Perform retry
                retry_count += 1
                if retry_count <= self.retries_times:
                    delay = base_delay * (2**retry_count)
                    print(f"Attempt {retry_count}, Retrying in {delay} seconds...")
                    await sleep(delay)
            # Raise an exception
            raise ConnectionError("Failed to get response.")

    return wrapper


class Connector:
    def __init__(self, ep_args: ConnectorEndpointArguments) -> None:
        self.id = ep_args.id

        self.endpoint = ep_args.uri
        self.token = ep_args.token
        self.max_concurrency = ep_args.max_concurrency
        self.max_calls_per_second = ep_args.max_calls_per_second
        self.params = ep_args.params

        self.pre_prompt = ""
        self.post_prompt = ""

        # Rate limiting
        self.rate_limiter = ep_args.max_calls_per_second
        self.semaphore = asyncio.Semaphore(ep_args.max_concurrency)
        self.last_call_time = None

        # Connection timeout
        self.timeout = ep_args.params.get("timeout", 600)
        self.allow_retries = ep_args.params.get("allow_retries", True)
        self.retries_times = ep_args.params.get("num_of_retries", 3)

    @staticmethod
    def rate_limited(func):
        """
        Decorator function to limit the rate of function calls.

        This decorator ensures that the decorated function is not called more frequently than the rate limit
        specified by the `rate_limiter` attribute of the `Connector` instance. If the function is called more
        frequently, it sleeps for the necessary amount of time to maintain the rate limit.

        Args:
            func (Callable): The function to be rate-limited.

        Returns:
            Callable: The wrapped function, which enforces the rate limit.
        """

        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            async with self.semaphore:
                if self.last_call_time is not None:
                    time_since_last_call = time.time() - self.last_call_time
                    if time_since_last_call < 1.0 / self.rate_limiter:
                        sleep_time = 1.0 / self.rate_limiter - time_since_last_call
                        print(
                            f"[{self.id}]: Hit rate-limit: Sleeping {round(sleep_time, 2)}s..."
                        )
                        await asyncio.sleep(sleep_time)
                self.last_call_time = time.time()
                return await func(self, *args, **kwargs)

        return wrapper

    @abstractmethod
    async def get_response(self, prompt: str) -> str:
        """
        Abstract method to be implemented by subclasses to get a response from the connector.

        This method should asynchronously send a prompt to the connector's API and return the response.

        Args:
            prompt (str): The input prompt to be sent to the connector.

        Returns:
            str: The response received from the connector.
        """
        pass

    @classmethod
    def load(cls, ep_args: ConnectorEndpointArguments) -> Connector:
        """
        Loads a connector instance based on the provided endpoint arguments.

        This method utilizes the connector type specified in the `ep_args` to dynamically load the corresponding
        connector class. It then instantiates the connector with the provided endpoint arguments. If the
        specified connector type does not match any available connector classes, a RuntimeError is raised.

        Args:
            ep_args (ConnectorEndpointArguments): The endpoint arguments containing the connector type and
            other necessary information.

        Returns:
            Connector: An instance of the specified connector class initialized with the given endpoint arguments.

        Raises:
            RuntimeError: If no connector class matches the specified connector type.
        """
        connector_instance = get_instance(
            ep_args.connector_type,
            StorageManager.get_connector_filepath(ep_args.connector_type),
        )
        if connector_instance:
            return connector_instance(ep_args)
        else:
            raise RuntimeError(
                f"Unable to get defined connector instance - {ep_args.connector_type}"
            )

    @staticmethod
    def create(ep_args: ConnectorEndpointArguments) -> Connector:
        """
        Creates a connector object based on the provided endpoint arguments.

        This method takes a ConnectorEndpointArguments object, which contains the necessary information
        to initialize and return a Connector object. The Connector object is created by calling the
        `load_connector` method, which dynamically loads and initializes the connector based on the
        endpoint arguments provided.

        Args:
            ep_args (ConnectorEndpointArguments): The endpoint arguments required to create the connector.

        Returns:
            Connector: An initialized Connector object based on the provided endpoint arguments.
        """
        try:
            return Connector.load(ep_args)

        except Exception as e:
            print(f"Failed to create connector: {str(e)}")
            raise e

    @staticmethod
    def get_available_items() -> list[str]:
        """
        Retrieves a list of all available connector types.

        This method uses the `StorageManager.get_connectors` method to find all Python files in the directory
        specified by the `EnvironmentVars.CONNECTORS` environment variable. It then filters out any files that are not
        meant to be exposed as connectors (those containing "__" in their names). The method returns a list of the
        names of these connector types.

        Returns:
            list[str]: A list of strings, each representing the name of a connector type.

        Raises:
            Exception: If there is an error during the retrieval of connector types.
        """
        try:
            return [
                Path(fp).stem
                for fp in StorageManager.get_connectors()
                if "__" not in fp
            ]

        except Exception as e:
            print(f"Failed to get available connectors: {str(e)}")
            raise e

    @staticmethod
    async def get_prediction(
        generated_prompt: PromptArguments,
        connector: Connector,
        prompt_callback: Union[Callable, None] = None,
    ) -> PromptArguments:
        """
        Generates a prediction for a given prompt using a specified connector.

        This method takes a `generated_prompt` object, which contains the prompt to be predicted, and a `connector`
        object, which is used to generate the prediction. The method also optionally takes a `prompt_callback` function,
        which is called after the prediction is generated.

        The method first prints a message indicating that it is predicting the prompt. It then records the start time
        and uses the `connector` to generate a prediction for the `generated_prompt`. The duration of the prediction
        is calculated and stored in the `generated_prompt`.

        If a `prompt_callback` function is provided, it is called with the `generated_prompt` and `connector.id` as
        arguments.

        The method then returns the `generated_prompt` with the generated prediction and duration.

        Args:
            generated_prompt (PromptArguments): The prompt to be predicted.
            connector (Connector): The connector to be used for prediction.
            prompt_callback (Union[Callable, None]): An optional callback function to be called after prediction.

        Returns:
            PromptArguments: The `generated_prompt` with the generated prediction and duration.

        Raises:
            Exception: If there is an error during prediction.
        """
        try:
            print(f"Predicting prompt {generated_prompt.prompt_index} [{connector.id}]")

            start_time = time.perf_counter()
            generated_prompt.predicted_results = await connector.get_response(
                generated_prompt.prompt
            )
            generated_prompt.duration = time.perf_counter() - start_time
            print(
                f"[Prompt {generated_prompt.prompt_index}] took {generated_prompt.duration:.4f}s"
            )

            # Call prompt callback
            if prompt_callback:
                prompt_callback(generated_prompt, connector.id)

            # Return the updated prompt
            return generated_prompt

        except Exception as e:
            print(f"Failed to get prediction: {str(e)}")
            raise e
