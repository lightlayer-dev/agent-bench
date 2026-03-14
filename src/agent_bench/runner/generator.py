"""Dynamic task generator — create tasks based on site classification."""

from __future__ import annotations

from agent_bench.runner.classifier import SiteCategory, SiteProfile
from agent_bench.runner.task import Task, TaskStep, SuccessCriterion


def generate_tasks(profile: SiteProfile) -> list[Task]:
    """Generate benchmark tasks based on the site's classification and features.

    Returns a list of tasks appropriate for the site type. Each task tests
    a specific capability that an agent would need to interact with this kind
    of site.
    """
    tasks: list[Task] = []

    # Universal tasks (work on any site)
    tasks.extend(_universal_tasks(profile))

    # Category-specific tasks
    generators = {
        SiteCategory.ECOMMERCE: _ecommerce_tasks,
        SiteCategory.SAAS: _saas_tasks,
        SiteCategory.DOCUMENTATION: _documentation_tasks,
        SiteCategory.SOCIAL: _social_tasks,
        SiteCategory.NEWS_MEDIA: _news_tasks,
        SiteCategory.SEARCH: _search_tasks,
        SiteCategory.API_SERVICE: _api_service_tasks,
        SiteCategory.FINANCE: _finance_tasks,
    }

    generator = generators.get(profile.category)
    if generator:
        tasks.extend(generator(profile))

    # Feature-based tasks (cross-category)
    if profile.has_search:
        tasks.append(Task(
            name="site-search",
            site=profile.url,
            description="Use the site's search functionality to find specific content",
            steps=[
                TaskStep(action="find_search", description="Locate the search input"),
                TaskStep(action="search", params={"query": "test"}, description="Enter a search query"),
                TaskStep(action="verify_results", description="Verify search results appeared"),
            ],
            success_criteria=[
                SuccessCriterion(type="text_contains", value="result", description="Search results should appear"),
            ],
            tags=["search", "universal"],
            difficulty="easy",
        ))

    if profile.has_auth:
        tasks.append(Task(
            name="find-login",
            site=profile.url,
            description="Navigate to the login page and identify the authentication flow",
            steps=[
                TaskStep(action="find_login", description="Locate and navigate to login page"),
                TaskStep(action="identify_auth", description="Identify auth method (form, OAuth, SSO)"),
            ],
            success_criteria=[
                SuccessCriterion(type="url_matches", value="*login*|*signin*|*auth*", description="Should reach a login page"),
            ],
            tags=["auth", "universal"],
            difficulty="easy",
        ))

    return tasks


def _universal_tasks(profile: SiteProfile) -> list[Task]:
    """Tasks that work on any website."""
    return [
        Task(
            name="navigate-home",
            site=profile.url,
            description="Navigate to the homepage and identify the primary content areas",
            steps=[
                TaskStep(action="navigate", params={"url": profile.url}),
                TaskStep(action="identify_structure", description="Identify nav, main content, footer"),
            ],
            success_criteria=[
                SuccessCriterion(type="element_exists", value="body", description="Page should load"),
            ],
            tags=["navigation", "universal"],
            difficulty="easy",
            expected_time_seconds=15,
        ),
        Task(
            name="extract-links",
            site=profile.url,
            description="Extract and categorize all navigation links from the homepage",
            steps=[
                TaskStep(action="navigate", params={"url": profile.url}),
                TaskStep(action="extract_links", description="Find all links in navigation"),
                TaskStep(action="categorize", description="Group links by section"),
            ],
            success_criteria=[
                SuccessCriterion(type="custom", value="links_extracted", description="Should extract at least 3 links"),
            ],
            tags=["navigation", "extraction", "universal"],
            difficulty="easy",
            expected_time_seconds=20,
        ),
    ]


def _ecommerce_tasks(profile: SiteProfile) -> list[Task]:
    """Tasks for e-commerce sites."""
    tasks = [
        Task(
            name="browse-products",
            site=profile.url,
            description="Browse the product catalog and find a specific category of items",
            steps=[
                TaskStep(action="navigate", params={"url": profile.url}),
                TaskStep(action="find_catalog", description="Navigate to product listing"),
                TaskStep(action="browse", description="Browse products, note prices and names"),
            ],
            success_criteria=[
                SuccessCriterion(type="text_contains", value="price", description="Should see product prices"),
            ],
            tags=["ecommerce", "browsing"],
            difficulty="medium",
            expected_time_seconds=45,
        ),
        Task(
            name="add-to-cart",
            site=profile.url,
            description="Find a product and add it to the shopping cart",
            steps=[
                TaskStep(action="navigate", params={"url": profile.url}),
                TaskStep(action="find_product", description="Select a product"),
                TaskStep(action="add_to_cart", description="Add the product to cart"),
                TaskStep(action="verify_cart", description="Verify item is in cart"),
            ],
            success_criteria=[
                SuccessCriterion(type="element_exists", value="[data-testid='cart']", description="Cart should show items"),
            ],
            tags=["ecommerce", "cart"],
            difficulty="medium",
            expected_time_seconds=60,
        ),
        Task(
            name="product-search-and-filter",
            site=profile.url,
            description="Search for a product, apply filters (price, category), and compare results",
            steps=[
                TaskStep(action="search", params={"query": "popular item"}, description="Search for a product"),
                TaskStep(action="apply_filter", description="Apply a price or category filter"),
                TaskStep(action="compare", description="Compare at least 2 results"),
            ],
            success_criteria=[
                SuccessCriterion(type="custom", value="filtered_results", description="Should see filtered results"),
            ],
            tags=["ecommerce", "search", "filtering"],
            difficulty="hard",
            expected_time_seconds=90,
        ),
    ]
    return tasks


def _saas_tasks(profile: SiteProfile) -> list[Task]:
    """Tasks for SaaS/product sites."""
    return [
        Task(
            name="find-pricing",
            site=profile.url,
            description="Navigate to the pricing page and extract plan details",
            steps=[
                TaskStep(action="find_pricing", description="Navigate to pricing page"),
                TaskStep(action="extract_plans", description="Extract plan names, prices, and features"),
            ],
            success_criteria=[
                SuccessCriterion(type="text_contains", value="price|plan|month|year", description="Should find pricing info"),
            ],
            tags=["saas", "pricing"],
            difficulty="easy",
            expected_time_seconds=30,
        ),
        Task(
            name="start-signup-flow",
            site=profile.url,
            description="Navigate to sign-up and identify required fields without submitting",
            steps=[
                TaskStep(action="find_signup", description="Navigate to sign-up page"),
                TaskStep(action="identify_fields", description="List all required form fields"),
            ],
            success_criteria=[
                SuccessCriterion(type="element_exists", value="form", description="Should find signup form"),
            ],
            tags=["saas", "auth", "forms"],
            difficulty="medium",
            expected_time_seconds=30,
        ),
    ]


def _documentation_tasks(profile: SiteProfile) -> list[Task]:
    """Tasks for documentation sites."""
    return [
        Task(
            name="find-api-reference",
            site=profile.url,
            description="Navigate the documentation to find API reference or getting started guide",
            steps=[
                TaskStep(action="navigate", params={"url": profile.url}),
                TaskStep(action="find_section", params={"target": "API reference or getting started"}),
                TaskStep(action="extract_info", description="Extract key information from the section"),
            ],
            success_criteria=[
                SuccessCriterion(type="text_contains", value="api|endpoint|method|request", description="Should find API docs"),
            ],
            tags=["docs", "navigation"],
            difficulty="easy",
            expected_time_seconds=30,
        ),
        Task(
            name="search-docs",
            site=profile.url,
            description="Search the documentation for a specific topic and extract relevant information",
            steps=[
                TaskStep(action="search", params={"query": "authentication"}, description="Search docs"),
                TaskStep(action="read_result", description="Read the most relevant result"),
                TaskStep(action="summarize", description="Summarize the key information"),
            ],
            success_criteria=[
                SuccessCriterion(type="custom", value="info_extracted", description="Should extract relevant info"),
            ],
            tags=["docs", "search"],
            difficulty="medium",
            expected_time_seconds=45,
        ),
    ]


def _social_tasks(profile: SiteProfile) -> list[Task]:
    """Tasks for social media sites."""
    return [
        Task(
            name="browse-feed",
            site=profile.url,
            description="Navigate to a public feed or profile and extract recent posts",
            steps=[
                TaskStep(action="navigate", params={"url": profile.url}),
                TaskStep(action="find_feed", description="Locate public feed or trending content"),
                TaskStep(action="extract_posts", description="Extract text from recent posts"),
            ],
            success_criteria=[
                SuccessCriterion(type="custom", value="posts_extracted", description="Should extract post content"),
            ],
            tags=["social", "browsing"],
            difficulty="medium",
            expected_time_seconds=45,
        ),
    ]


def _news_tasks(profile: SiteProfile) -> list[Task]:
    """Tasks for news/media sites."""
    return [
        Task(
            name="read-headline-article",
            site=profile.url,
            description="Find the top headline and extract the full article text",
            steps=[
                TaskStep(action="navigate", params={"url": profile.url}),
                TaskStep(action="find_headline", description="Identify the top headline"),
                TaskStep(action="read_article", description="Navigate to and read the full article"),
            ],
            success_criteria=[
                SuccessCriterion(type="custom", value="article_extracted", description="Should extract article text"),
            ],
            tags=["news", "reading"],
            difficulty="easy",
            expected_time_seconds=30,
        ),
    ]


def _search_tasks(profile: SiteProfile) -> list[Task]:
    """Tasks for search engine sites."""
    return [
        Task(
            name="web-search",
            site=profile.url,
            description="Perform a search query and extract the top results",
            steps=[
                TaskStep(action="search", params={"query": "OpenAI API documentation"}),
                TaskStep(action="extract_results", description="Extract titles, URLs, and snippets from results"),
            ],
            success_criteria=[
                SuccessCriterion(type="custom", value="results_extracted", description="Should extract search results"),
            ],
            tags=["search"],
            difficulty="easy",
            expected_time_seconds=20,
        ),
    ]


def _api_service_tasks(profile: SiteProfile) -> list[Task]:
    """Tasks for API/developer service sites."""
    return [
        Task(
            name="find-api-docs",
            site=profile.url,
            description="Locate API documentation, find authentication method, and identify available endpoints",
            steps=[
                TaskStep(action="find_docs", description="Navigate to API documentation"),
                TaskStep(action="find_auth", description="Identify authentication method"),
                TaskStep(action="list_endpoints", description="List available API endpoints"),
            ],
            success_criteria=[
                SuccessCriterion(type="text_contains", value="api|endpoint|auth", description="Should find API info"),
            ],
            tags=["api", "docs"],
            difficulty="medium",
            expected_time_seconds=45,
        ),
    ]


def _finance_tasks(profile: SiteProfile) -> list[Task]:
    """Tasks for finance/banking sites."""
    return [
        Task(
            name="find-account-info",
            site=profile.url,
            description="Navigate to find account information or financial product details",
            steps=[
                TaskStep(action="navigate", params={"url": profile.url}),
                TaskStep(action="find_products", description="Find financial products or account types"),
                TaskStep(action="extract_details", description="Extract key terms and rates"),
            ],
            success_criteria=[
                SuccessCriterion(type="text_contains", value="rate|account|apr", description="Should find financial info"),
            ],
            tags=["finance", "browsing"],
            difficulty="medium",
            expected_time_seconds=45,
        ),
    ]
