#!/usr/bin/env python3
"""
Update Wiki.js with LLM Backend System documentation.

Creates comprehensive documentation for the new LLM backend system and
marks old Athena pages as deprecated.
"""
import requests
import json
import sys
from typing import Dict, List, Optional

WIKI_URL = "https://wiki.xmojo.net/graphql"
API_KEY = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcGkiOjEsImdycCI6MSwiaWF0IjoxNzYxMDE3MjIwLCJleHAiOjE4NTU2OTAwMjAsImF1ZCI6InVybjp3aWtpLmpzIiwiaXNzIjoidXJuOndpa2kuanMifQ.uVf1EWBUCVtiEd8vyPoT0-xWQa20mxlVbmPbo29mCGMt_fjqR0RkplgT6oYXvUKk5EiCyPz6fgVGhFpDlphEoLKpJ9n0QvAYuGRMkor-lqjbhRf0eXcDcBGBFSDJ4LWkqoD-DdTQq4Yt9NOCi_ZV__8FFDdMr2DEcML4HHKV5F2tCaqABo3CD_E9CXZ1Gdmsynba2xJAEvhDnTQxMJsEPVZ4clwbnZVcmM1IX816ucyJAr4Ht3_dQbIRdtNnAYvoW-FU0BftArs3yKCXy-nsftC-kvIiTRgbibmPly3TPTfr-FuxhU_1J94Bbas1x91nLHwqZ2E8gZgLFxt2drtQ0A"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}


def graphql_query(query: str, variables: Dict = None) -> Dict:
    """Execute GraphQL query against Wiki.js"""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    # Debug: print request
    # print(f"DEBUG Request: {json.dumps(payload, indent=2)}")

    response = requests.post(WIKI_URL, json=payload, headers=HEADERS, verify=False)

    # Get response text for debugging
    response_text = response.text

    # Try to parse JSON
    try:
        result = response.json()
    except Exception as e:
        print(f"Failed to parse JSON response: {response_text}")
        raise

    if "errors" in result:
        print(f"GraphQL errors:")
        for error in result['errors']:
            print(f"  - {error.get('message', error)}")
            if 'extensions' in error:
                print(f"    Extensions: {error['extensions']}")
        raise Exception(f"GraphQL query failed")

    if response.status_code >= 400:
        print(f"HTTP {response.status_code}: {response_text}")
        response.raise_for_status()

    return result.get("data", {})


def search_pages(query: str) -> List[Dict]:
    """Search for existing pages"""
    gql = """
    query SearchPages($query: String!) {
      pages {
        search(query: $query) {
          results {
            id
            path
            title
          }
        }
      }
    }
    """

    result = graphql_query(gql, {"query": query})
    return result.get("pages", {}).get("search", {}).get("results", [])


def create_page(path: str, title: str, content: str, description: str = "", tags: List[str] = None) -> Dict:
    """Create a new Wiki page"""
    gql = """
    mutation CreatePage(
      $content: String!
      $description: String!
      $editor: String!
      $isPublished: Boolean!
      $isPrivate: Boolean!
      $locale: String!
      $path: String!
      $publishEndDate: Date
      $publishStartDate: Date
      $tags: [String]!
      $title: String!
    ) {
      pages {
        create(
          content: $content
          description: $description
          editor: $editor
          isPublished: $isPublished
          isPrivate: $isPrivate
          locale: $locale
          path: $path
          publishEndDate: $publishEndDate
          publishStartDate: $publishStartDate
          tags: $tags
          title: $title
        ) {
          responseResult {
            succeeded
            errorCode
            slug
            message
          }
          page {
            id
            path
            title
          }
        }
      }
    }
    """

    variables = {
        "content": content,
        "description": description,
        "editor": "markdown",
        "isPublished": True,
        "isPrivate": False,
        "locale": "en",
        "path": path,
        "publishEndDate": None,
        "publishStartDate": None,
        "tags": tags or [],
        "title": title
    }

    result = graphql_query(gql, variables)
    return result.get("pages", {}).get("create", {})


def update_page(page_id: int, content: str, title: Optional[str] = None, tags: List[str] = None) -> Dict:
    """Update an existing Wiki page"""
    gql = """
    mutation UpdatePage(
      $id: Int!
      $content: String!
      $title: String
      $tags: [String]
      $isPublished: Boolean
    ) {
      pages {
        update(
          id: $id
          content: $content
          title: $title
          tags: $tags
          isPublished: $isPublished
        ) {
          responseResult {
            succeeded
            errorCode
            message
          }
          page {
            id
            path
            title
          }
        }
      }
    }
    """

    variables = {
        "id": page_id,
        "content": content,
        "isPublished": True
    }

    if title:
        variables["title"] = title
    if tags:
        variables["tags"] = tags

    result = graphql_query(gql, variables)
    return result.get("pages", {}).get("update", {})


def main():
    """Main execution"""
    print("🚀 Updating Wiki.js with LLM Backend System documentation...")

    # Define documentation pages
    pages = [
        {
            "path": "homelab/projects/project-athena/llm-backend-overview",
            "title": "LLM Backend System - Overview",
            "description": "Overview of the flexible LLM backend selection system for Project Athena",
            "tags": ["athena", "llm", "backend", "architecture"],
            "content": open("wiki_content/llm-backend-overview.md").read()
        },
        {
            "path": "homelab/projects/project-athena/llm-backend-admin-api",
            "title": "LLM Backend System - Admin API",
            "description": "Admin API reference for managing LLM backend configurations",
            "tags": ["athena", "llm", "api", "admin"],
            "content": open("wiki_content/llm-backend-admin-api.md").read()
        },
        {
            "path": "homelab/projects/project-athena/llm-backend-router",
            "title": "LLM Backend System - Router Technical Docs",
            "description": "Technical documentation for the LLM Router component",
            "tags": ["athena", "llm", "router", "technical"],
            "content": open("wiki_content/llm-backend-router.md").read()
        },
        {
            "path": "homelab/projects/project-athena/llm-backend-config",
            "title": "LLM Backend System - Configuration Guide",
            "description": "Step-by-step guide for configuring LLM backends",
            "tags": ["athena", "llm", "configuration", "howto"],
            "content": open("wiki_content/llm-backend-config.md").read()
        },
        {
            "path": "homelab/projects/project-athena/llm-backend-deployment",
            "title": "LLM Backend System - Deployment Guide",
            "description": "Deployment procedures and operational guidance",
            "tags": ["athena", "llm", "deployment", "operations"],
            "content": open("wiki_content/llm-backend-deployment.md").read()
        }
    ]

    # Create pages
    for page in pages:
        print(f"\n📄 Creating page: {page['title']}")
        try:
            result = create_page(
                path=page["path"],
                title=page["title"],
                content=page["content"],
                description=page["description"],
                tags=page["tags"]
            )

            if result.get("responseResult", {}).get("succeeded"):
                print(f"   ✅ Successfully created: {page['path']}")
            else:
                error_msg = result.get("responseResult", {}).get("message", "Unknown error")
                print(f"   ❌ Failed: {error_msg}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

    # Search for old Athena pages to mark as deprecated
    print("\n🔍 Searching for old Athena pages to mark as deprecated...")
    old_pages = search_pages("project-athena")

    deprecated_paths = [
        "homelab/projects/project-athena"  # Main page - will add deprecation notice
    ]

    for old_page in old_pages:
        if any(dep in old_page['path'] for dep in deprecated_paths) and "llm-backend" not in old_page['path']:
            print(f"   ⚠️  Found old page: {old_page['title']} ({old_page['path']})")
            print(f"      Manual review recommended for deprecation")

    print("\n✅ Wiki documentation update complete!")
    print("\nNext steps:")
    print("1. Visit https://wiki.xmojo.net/homelab/projects/project-athena/llm-backend-overview")
    print("2. Review all new pages")
    print("3. Update navigation/index pages")
    print("4. Add deprecation notices to old pages")


if __name__ == "__main__":
    main()
