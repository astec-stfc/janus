"""GraphQL router for integrating GraphQL endpoint into FastAPI"""

from strawberry.fastapi import GraphQLRouter

from gql.schemas import schema

# Create GraphQL router with the schema
graphql_router = GraphQLRouter(schema)

# Export for use in main.py
__all__ = ["graphql_router"]
