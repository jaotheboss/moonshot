import asyncio
from moonshot.src.api.api_runner import (
    api_create_runner, api_delete_runner, api_get_all_runner, 
    api_get_all_runner_name, api_load_runner, api_read_runner
)
from moonshot.src.runners.runner_type import RunnerType

# ------------------------------------------------------------------------------
# Support Functions
# ------------------------------------------------------------------------------
def runner_callback_fn(progress_args: dict):
    print("=" * 100)
    print("PROGRESS CALLBACK FN: ", progress_args)
    print("=" * 100)

def test_create_runner(name: str):
    runner = api_create_runner(
        name=name,
        endpoints=["openai-gpt35-lionel", "openai-gpt35-turbo-16k-lionel"],
        progress_callback_func=runner_callback_fn,
    )
    print("Runner Attributes:")
    print("ID:", runner.id)
    print("Name:", runner.name)
    print("Endpoints:", runner.endpoints)
    print("Database Instance:", runner.database_instance)
    print("Database File:", runner.database_file)
    print("Progress Callback Function:", runner.progress_callback_func)
    runner.close()

def test_load_runner(runner_id: str):
    runner = api_load_runner(runner_id, progress_callback_func=runner_callback_fn)
    print("Runner Attributes:")
    print("ID:", runner.id)
    print("Name:", runner.name)
    print("Endpoints:", runner.endpoints)
    print("Database Instance:", runner.database_instance)
    print("Database File:", runner.database_file)
    print("Progress Callback Function:", runner.progress_callback_func)
    runner.close()

def test_run_runner(runner_id: str):
    runner = api_load_runner(runner_id, progress_callback_func=runner_callback_fn)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        runner.run(RunnerType.BENCHMARK, {
            "recipes": ["bbq", "autocategorisation"],
            "num_of_prompts": 2,
            "runner_processing_module": "benchmarking"
        })
    )

def test_run_benchmark_recipe_runner_and_cancel(runner_id: str):
    async def run_and_cancel():
        runner = api_load_runner(runner_id, progress_callback_func=runner_callback_fn)
        
        # Run the recipes in a background task
        run_task = asyncio.create_task(runner.run_recipes(["cbbq-lite", "advglue-mnli"], 2))

        # Wait for 1 second before cancelling
        await asyncio.sleep(1)
        await runner.cancel()

        # Wait for the run task to complete
        await run_task
        runner.close()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        run_and_cancel()
    )

def test_run_benchmark_cookbook_runner_and_cancel(runner_id: str):
    async def run_and_cancel():
        runner = api_load_runner(runner_id, progress_callback_func=runner_callback_fn)
        
        # Run the cookbooks in a background task
        run_task = asyncio.create_task(runner.run_cookbooks(["tamil-language-cookbook","cbbq-amb-cookbook"], 2))

        # Wait for 1 second before cancelling
        await asyncio.sleep(1)
        await runner.cancel()

        # Wait for the run task to complete
        await run_task
        runner.close()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        run_and_cancel()
    )

def test_run_benchmark_recipe_runner(runner_id: str):
    runner = api_load_runner(runner_id, progress_callback_func=runner_callback_fn)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        runner.run_recipes(
            ["bbq", "auto-categorisation"],
            2,
            2
        )
    )
    runner.close()

def test_run_benchmark_cookbook_runner(runner_id: str):
    runner = api_load_runner(runner_id, progress_callback_func=runner_callback_fn)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        runner.run_cookbooks(
            ["common-risk-easy","leaderboard-cookbook"],
            2,
            2
        )
    )
    runner.close()

def test_read_runner(runner_id: str):
    print(api_read_runner(runner_id))

def test_delete_runner(runner_id: str):
    # Delete result if do not exists
    try:
        api_delete_runner("runner123")
        print("Delete runner if exist: FAILED")
    except Exception as ex:
        print(f"Delete runner if do not exist: PASSED")

    # Delete result if exists
    try:
        api_delete_runner(runner_id)
        print("Delete runner if exist: PASSED")
    except Exception:
        print("Delete runner if exist: FAILED")

def test_get_all_runner():
    print(api_get_all_runner())

def test_get_all_runner_name():
    print(api_get_all_runner_name())

# ------------------------------------------------------------------------------
# Run Runner Functions
# ------------------------------------------------------------------------------
def test_run_runner_api():
    runner_name = "my new runner"
    runner_id = "my-new-runner"

    # Create runner
    print("=" * 100, "\nTest creating runner")
    test_create_runner(runner_name)

    # Load runner
    print("=" * 100, "\nTest loading runner")
    test_load_runner(runner_id)

    # Run the benchmark runner job
    print("=" * 100, "\nTest running runner")
    test_run_benchmark_recipe_runner(runner_id)
    test_run_benchmark_cookbook_runner(runner_id)

    # Run the benchmark runner job and cancel
    print("=" * 100, "\nTest running runner and cancelling job")
    test_run_benchmark_recipe_runner_and_cancel(runner_id)
    test_run_benchmark_cookbook_runner_and_cancel(runner_id)

    # Read runner
    print("=" * 100, "\nTest reading runner")
    test_read_runner(runner_id)

    # List all runner
    print("=" * 100, "\nTest listing all runner")
    test_get_all_runner()

    # List all runner names
    print("=" * 100, "\nTest listing all runner name")
    test_get_all_runner_name()

    # Delete runner
    print("=" * 100, "\nTest deleting runners")
    test_delete_runner(runner_id)
