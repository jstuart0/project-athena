#!/usr/bin/env python3
"""
Initialize Qdrant vector database for Project Athena.

This script creates the athena_knowledge collection with the correct
vector configuration for storing knowledge embeddings.

Usage:
    python scripts/init_qdrant.py

Requirements:
    pip install qdrant-client

Configuration:
    - Collection: athena_knowledge
    - Vector size: 384 dimensions (all-MiniLM-L6-v2)
    - Distance metric: Cosine similarity
    - Qdrant URL: http://192.168.10.29:6333 (or localhost if running on Mac mini)
"""

import os
import sys
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from qdrant_client.http.exceptions import UnexpectedResponse

# Configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://192.168.10.29:6333")
COLLECTION_NAME = "athena_knowledge"
VECTOR_SIZE = 384  # sentence-transformers/all-MiniLM-L6-v2
DISTANCE_METRIC = Distance.COSINE


def main():
    """Initialize Qdrant collection for Project Athena."""
    print(f"🚀 Initializing Qdrant at {QDRANT_URL}")
    print(f"📦 Collection: {COLLECTION_NAME}")
    print(f"📏 Vector size: {VECTOR_SIZE} dimensions")
    print(f"📐 Distance metric: {DISTANCE_METRIC}")
    print()

    try:
        # Connect to Qdrant
        client = QdrantClient(url=QDRANT_URL)

        # Check connection
        print("🔌 Testing connection...")
        collections = client.get_collections()
        print(f"✅ Connected! Found {len(collections.collections)} existing collections")
        print()

        # Check if collection already exists
        existing_collections = [c.name for c in collections.collections]

        if COLLECTION_NAME in existing_collections:
            print(f"⚠️  Collection '{COLLECTION_NAME}' already exists!")
            response = input("Do you want to recreate it? This will DELETE all data. (yes/no): ")

            if response.lower() == 'yes':
                print(f"🗑️  Deleting existing collection '{COLLECTION_NAME}'...")
                client.delete_collection(collection_name=COLLECTION_NAME)
                print("✅ Deleted")
                print()
            else:
                print("❌ Aborted. Keeping existing collection.")
                return

        # Create collection
        print(f"📦 Creating collection '{COLLECTION_NAME}'...")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=DISTANCE_METRIC
            )
        )
        print("✅ Collection created successfully!")
        print()

        # Verify collection
        print("🔍 Verifying collection...")
        collection_info = client.get_collection(collection_name=COLLECTION_NAME)
        print(f"   Name: {collection_info.name}")
        print(f"   Vectors: {collection_info.vectors_count}")
        print(f"   Points: {collection_info.points_count}")
        print(f"   Status: {collection_info.status}")
        print()

        # Insert a test point to verify functionality
        print("🧪 Inserting test point...")
        test_vector = [0.1] * VECTOR_SIZE  # Simple test vector
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                PointStruct(
                    id=1,
                    vector=test_vector,
                    payload={
                        "text": "Test knowledge entry for Project Athena",
                        "source": "initialization_script",
                        "category": "test"
                    }
                )
            ]
        )
        print("✅ Test point inserted")
        print()

        # Search for the test point to verify search works
        print("🔍 Testing search functionality...")
        search_results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=test_vector,
            limit=1
        )

        if search_results and len(search_results) > 0:
            print("✅ Search successful!")
            print(f"   Found: {search_results[0].payload.get('text')}")
            print(f"   Score: {search_results[0].score:.4f}")
        else:
            print("⚠️  Search returned no results (unexpected)")
        print()

        # Clean up test point
        print("🧹 Cleaning up test point...")
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=[1]
        )
        print("✅ Test point removed")
        print()

        # Final status
        print("=" * 60)
        print("✅ Qdrant initialization complete!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("  1. Deploy RAG services that will populate this collection")
        print("  2. Configure embedding model (all-MiniLM-L6-v2)")
        print("  3. Start indexing knowledge sources")
        print()
        print("Access Qdrant:")
        print(f"  Dashboard: {QDRANT_URL}/dashboard")
        print(f"  API: {QDRANT_URL}")
        print()

    except UnexpectedResponse as e:
        print(f"❌ Qdrant error: {e}")
        print()
        print("Troubleshooting:")
        print(f"  1. Verify Qdrant is running: curl {QDRANT_URL}/healthz")
        print(f"  2. Check Mac mini is accessible at 192.168.10.29")
        print(f"  3. Verify Docker services: docker ps")
        sys.exit(1)

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print()
        print("Please check:")
        print(f"  - Qdrant is running at {QDRANT_URL}")
        print(f"  - qdrant-client is installed: pip install qdrant-client")
        print(f"  - Network connectivity to Mac mini")
        sys.exit(1)


if __name__ == "__main__":
    main()
