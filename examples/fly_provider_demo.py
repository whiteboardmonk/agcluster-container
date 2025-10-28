"""
Demo: Using Fly Machines Provider with AgCluster

This example demonstrates how to use the Fly provider to deploy
Claude Agent SDK containers on Fly.io infrastructure.

Prerequisites:
1. Fly.io account and flyctl CLI installed
2. Fly app created: flyctl apps create agcluster-agents
3. Agent image pushed to Fly registry
4. Fly API token: flyctl auth token
5. Anthropic API key
"""

import asyncio
import os
from agcluster.container.core.providers import ProviderFactory, ProviderConfig


async def main():
    """Demo: Create and query agent on Fly.io"""

    # Configuration
    FLY_API_TOKEN = os.getenv("FLY_API_TOKEN", "your_fly_token_here")
    FLY_APP_NAME = os.getenv("FLY_APP_NAME", "agcluster-agents")
    FLY_REGION = os.getenv("FLY_REGION", "iad")  # US East
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "sk-ant-...")

    print("=== Fly Machines Provider Demo ===\n")

    # Step 1: Create Fly provider instance
    print("1. Creating Fly provider...")
    provider = ProviderFactory.create_provider(
        platform="fly_machines",
        api_token=FLY_API_TOKEN,
        app_name=FLY_APP_NAME,
        region=FLY_REGION,
        image=f"registry.fly.io/{FLY_APP_NAME}:latest",
    )
    print(f"   ✓ Provider created: {type(provider).__name__}")
    print(f"   ✓ App: {FLY_APP_NAME}")
    print(f"   ✓ Region: {FLY_REGION}\n")

    # Step 2: Configure agent
    print("2. Configuring agent...")
    config = ProviderConfig(
        platform="fly_machines",
        cpu_quota=200000,  # 2 CPUs
        memory_limit="4g",
        storage_limit="10g",
        allowed_tools=["Bash", "Read", "Write", "Grep"],
        system_prompt="You are a helpful coding assistant running on Fly.io.",
        max_turns=50,
        api_key=ANTHROPIC_API_KEY,
        platform_credentials={
            "fly_region": FLY_REGION  # Can override per-agent
        },
    )
    print(f"   ✓ Platform: {config.platform}")
    print(f"   ✓ Resources: 2 CPUs, 4GB RAM")
    print(f"   ✓ Tools: {len(config.allowed_tools)}")
    print(f"   ✓ Max turns: {config.max_turns}\n")

    # Step 3: Create machine on Fly.io
    print("3. Creating Fly Machine...")
    try:
        container_info = await provider.create_container(
            session_id="demo-session-123", config=config
        )
        print(f"   ✓ Machine created: {container_info.container_id}")
        print(f"   ✓ Endpoint: {container_info.endpoint_url}")
        print(f"   ✓ Status: {container_info.status}")
        print(f"   ✓ Region: {container_info.metadata.get('region', 'unknown')}")
        print(f"   ✓ Private IP: {container_info.metadata.get('private_ip', 'unknown')}\n")
    except Exception as e:
        print(f"   ✗ Error creating machine: {e}")
        return

    # Step 4: Execute query
    print("4. Executing query...")
    query = "Write a simple Python function to calculate factorial"
    print(f"   Query: '{query}'\n")

    try:
        print("   Response:")
        async for message in provider.execute_query(
            container_info=container_info, query=query, conversation_history=[]
        ):
            if message["type"] == "message":
                content = message.get("content", "")
                if content:
                    print(f"     {content[:100]}...")
            elif message["type"] == "complete":
                print(f"\n   ✓ Query completed: {message.get('status', 'unknown')}")
    except Exception as e:
        print(f"   ✗ Error executing query: {e}")

    # Step 5: Check machine status
    print("\n5. Checking machine status...")
    status = await provider.get_container_status(container_info.container_id)
    print(f"   ✓ Status: {status}")

    # Step 6: List active machines
    print("\n6. Listing active machines...")
    containers = await provider.list_containers()
    print(f"   ✓ Active machines: {len(containers)}")
    for c in containers:
        print(f"     - {c.container_id} ({c.status})")

    # Step 7: Stop machine
    print("\n7. Stopping machine...")
    result = await provider.stop_container(container_info.container_id)
    if result:
        print(f"   ✓ Machine stopped and destroyed")
    else:
        print(f"   ✗ Failed to stop machine")

    # Step 8: Cleanup
    print("\n8. Cleanup...")
    await provider.cleanup()
    print(f"   ✓ Provider cleaned up\n")

    print("=== Demo Complete ===")


async def regional_deployment_demo():
    """Demo: Deploy agents to multiple regions"""

    print("\n=== Multi-Region Deployment Demo ===\n")

    FLY_API_TOKEN = os.getenv("FLY_API_TOKEN", "your_fly_token_here")
    FLY_APP_NAME = os.getenv("FLY_APP_NAME", "agcluster-agents")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "sk-ant-...")

    # Deploy to 3 regions
    regions = ["iad", "lhr", "nrt"]  # US, Europe, Asia

    providers = {}
    containers = {}

    print("1. Creating providers in multiple regions...")
    for region in regions:
        providers[region] = ProviderFactory.create_provider(
            platform="fly_machines",
            api_token=FLY_API_TOKEN,
            app_name=FLY_APP_NAME,
            region=region,
            image=f"registry.fly.io/{FLY_APP_NAME}:latest",
        )
        print(f"   ✓ Provider created: {region}")

    print("\n2. Deploying machines in each region...")
    config = ProviderConfig(
        platform="fly_machines",
        cpu_quota=100000,  # 1 CPU (cost-effective for demo)
        memory_limit="2g",
        storage_limit="5g",
        allowed_tools=["Bash", "Read", "Write"],
        system_prompt="You are a globally distributed AI assistant.",
        max_turns=20,
        api_key=ANTHROPIC_API_KEY,
        platform_credentials={},
    )

    for region, provider in providers.items():
        try:
            container_info = await provider.create_container(
                session_id=f"session-{region}", config=config
            )
            containers[region] = container_info
            print(
                f"   ✓ {region}: {container_info.container_id} @ {container_info.metadata.get('private_ip')}"
            )
        except Exception as e:
            print(f"   ✗ {region}: Failed - {e}")

    print("\n3. Cleanup all regions...")
    for region, provider in providers.items():
        await provider.cleanup()
        print(f"   ✓ {region} cleaned up")

    print("\n=== Multi-Region Demo Complete ===")


if __name__ == "__main__":
    # Run basic demo
    asyncio.run(main())

    # Uncomment to run multi-region demo
    # asyncio.run(regional_deployment_demo())
