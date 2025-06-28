# Gender Filter Implementation Summary

## Overview
Implemented gender filter functionality for lawyer matching to allow users to specify their preference for male or female attorneys.

## Changes Made

### 1. **MatcherAgent** (`src/agents/matcher_agent.py`)
- Added gender preference filter in `_build_filter_query` method (line 259-261)
- Added gender field to LawyerCard formatting in `_format_lawyer_cards` method (line 357)

### 2. **ElasticsearchService** (`src/services/elasticsearch_service.py`)
- Added gender filter support in `_build_filter_queries` method (line 504-508)

### 3. **LawyerCard Model** (`src/models/conversation.py`)
- Added optional `gender` field to LawyerCard model (line 61)

### 4. **SignalExtractAgent** (`src/agents/signal_extract.py`)
- Updated extraction prompt to explicitly mention gender preferences (line 61)

### 5. **EnhancedMatcherAgent** (`src/agents/enhanced_matcher.py`)
- Added gender preference to preference query (line 253)
- Added gender filter to search execution (line 395-396)

## Usage

### User Input Examples
- "I need a female divorce lawyer in Chicago"
- "Looking for a male attorney for child custody"
- "I prefer a woman lawyer who specializes in family law"

### How It Works
1. **Signal Extraction**: The SignalExtractAgent extracts gender preference from user text and stores it as `gender_preference` in facts
2. **Filter Building**: MatcherAgent builds filter query including gender preference
3. **Search**: ElasticsearchService applies gender filter when searching lawyers
4. **Results**: LawyerCard includes gender information for display

### Testing
Run the test script to verify functionality:
```bash
python test_gender_filter.py
```

## Notes
- Gender field is already defined in Elasticsearch mapping as a keyword field
- Filter is case-sensitive (values should be lowercase: "male", "female")
- Gender preference is optional - if not specified, all lawyers are returned
- The implementation respects user autonomy by only filtering when explicitly requested