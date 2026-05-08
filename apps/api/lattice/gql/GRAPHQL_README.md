# GraphQL Service Integration

The lattice-api now includes a GraphQL endpoint for querying the lattice database using flexible partial lattice definitions.

## Endpoint

The GraphQL endpoint is available at:
```
POST /graphql
GET /graphql  (for interactive playground)
```

## Features

- **Flexible Querying**: Query lattices using partial definitions - only specify the fields you need
- **Multiple Query Types**: Find lattices, get facilities, retrieve section information
- **Interactive Playground**: Built-in GraphQL explorer at `/graphql`
- **Type-Safe**: Full type definitions for all queries and responses

## Installation

Add strawberry-graphql to your dependencies:

```bash
pip install strawberry-graphql[fastapi]
```

## Usage Examples

### Find lattices by facility

```graphql
query {
  findLattices(filter: {facility: "CLARA"}) {
    uuid
    facility
    sectionCount
  }
}
```

### Find lattices with specific sections

```graphql
query {
  findLattices(filter: {
    sections: [{name: "section1"}]
  }) {
    uuid
    facility
    setInitialConditions
    sectionCount
  }
}
```

### Find lattices with section and model match

```graphql
query {
  findLattices(filter: {
    sections: [{name: "section1", model: "my_model"}]
  }) {
    uuid
    facility
  }
}
```

### Get all facilities

```graphql
query {
  getFacilities {
    name
    latticeCount
  }
}
```

### Get section names for a facility

```graphql
query {
  getSectionNames(facility: "CLARA") {
    name
    facility
    count
  }
}
```

### Get section names across all facilities

```graphql
query {
  getSectionNames {
    name
    facility
    count
  }
}
```

### Get specific lattice by UUID

```graphql
query {
  getLatticByUuid(uuid: "your-uuid-here") {
    uuid
    facility
    setInitialConditions
    sectionCount
  }
}
```

## API Reference

### Queries

#### `findLattices(filter: PartialLatticeFilterInput!): [LatticeResult!]!`

Find lattices matching the provided filter criteria. All filter fields are optional.

**Input:**
- `filter.facility` (String, optional) - Filter by facility name
- `filter.setInitialConditions` (String, optional) - Filter by initial conditions setting
- `filter.sections` (List of PartialSectionInput, optional) - Filter by sections
  - `name` (String, optional) - Section name
  - `model` (String, optional) - Section model

**Returns:**
- `uuid` (String) - Lattice UUID
- `facility` (String) - Facility name
- `setInitialConditions` (String) - Initial conditions setting
- `sectionCount` (Int) - Number of sections in lattice

#### `getFacilities: [FacilityInfo!]!`

Get all available facilities with their lattice counts.

**Returns:**
- `name` (String) - Facility name
- `latticeCount` (Int) - Number of lattices in facility

#### `getSectionNames(facility: String): [SectionInfo!]!`

Get all section names, optionally filtered by facility.

**Input:**
- `facility` (String, optional) - Filter by facility

**Returns:**
- `name` (String) - Section name
- `facility` (String, optional) - Facility name
- `count` (Int) - Number of sections with this name

#### `getLatticByUuid(uuid: String!): LatticeResult`

Get a specific lattice by UUID.

**Input:**
- `uuid` (String, required) - Lattice UUID

**Returns:**
- `uuid` (String) - Lattice UUID
- `facility` (String) - Facility name
- `setInitialConditions` (String) - Initial conditions setting
- `sectionCount` (Int) - Number of sections

## Architecture

The GraphQL service is organized as follows:

```
graphql_service/
├── __init__.py              # Package exports
├── graphql_schema.py        # GraphQL type definitions
├── graphql_resolvers.py     # Query resolvers
└── graphql_router.py        # FastAPI router setup
```

### Module Descriptions

- **graphql_schema.py**: Defines the GraphQL schema using Strawberry, including:
  - Input types for flexible filtering (PartialLatticeFilterInput, PartialSectionInput)
  - Output types for results (LatticeResult, FacilityInfo, SectionInfo)
  - Query definitions

- **graphql_resolvers.py**: Implements the actual query logic:
  - Connects to the database using SQLAlchemy
  - Performs partial matching on lattices
  - Handles all filtering logic

- **graphql_router.py**: Sets up the Strawberry GraphQL router for FastAPI integration

## How Partial Matching Works

The `_partial_match()` function in `graphql_resolvers.py` implements flexible filtering:

1. **Facility Matching**: Only checks facility if provided in filter
2. **Initial Conditions Matching**: Only checks if provided in filter
3. **Section Matching**: 
   - If sections are provided, verifies all specified sections exist
   - Only checks model if provided in section filter
   - Allows matching a subset of a lattice's sections

This allows users to query with as little or as much detail as needed.

## Error Handling

All resolvers include try-catch blocks to handle:
- Database connection errors
- Invalid query parameters
- Missing data
- Type conversion errors

Errors are logged and return empty results gracefully.

## Performance Considerations

- Database queries use SQLAlchemy for efficient filtering
- Count operations use SQL aggregation functions
- Session management prevents connection leaks
- Joins are used for multi-table queries

## Testing

To test the GraphQL endpoint:

1. Start the lattice-api service
2. Navigate to `http://localhost:8000/graphql`
3. Use the interactive playground to write and execute queries

## Future Enhancements

Potential improvements:
- Add mutations for creating/updating lattices
- Add pagination support for large result sets
- Add sorting options
- Add caching for frequently queried data
- Add subscriptions for real-time updates
