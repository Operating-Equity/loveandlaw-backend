"""
Script to load lawyer data from CSV files into Elasticsearch.
Processes the data according to the mapping structure defined in models/elasticsearch_mapping.py
"""

import asyncio
import csv
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
from datetime import datetime
import sys

# Add parent directory to path to import from src
sys.path.append(str(Path(__file__).parent.parent))

from src.services.elasticsearch_service import elasticsearch_service
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class LawyerDataLoader:
    """Loads and transforms lawyer data from CSV files into Elasticsearch."""

    def __init__(self, data_dir: str = "./.data"):
        self.data_dir = Path(data_dir)
        self.merged_lawyers = {}
        self.normalized_mapping = {}
        self.locations = {}
        self.source_data = {}
        self.reviews = {}
        self.scorecards = {}

    async def load_all_data(self):
        """Load all CSV files and populate Elasticsearch."""
        try:
            # Initialize Elasticsearch
            await elasticsearch_service.initialize()
            logger.info("Connected to Elasticsearch")

            # Load data files in order
            logger.info("Loading CSV files...")
            self._load_scorecard_weights()
            self._load_normalized_mapping()
            self._load_merged_lawyers()
            self._load_locations()
            self._load_source_data()
            self._load_reviews()

            # Transform and index data
            logger.info("Transforming and indexing lawyer data...")
            lawyers_to_index = self._transform_lawyers()

            # Bulk index lawyers
            result = await elasticsearch_service.bulk_index_lawyers(
                lawyers_to_index,
                batch_size=500
            )

            logger.info(f"Indexing complete: {result['indexed']} lawyers indexed, {len(result['errors'])} errors")

            if result['errors']:
                logger.error(f"First 5 errors: {result['errors'][:5]}")

        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise
        finally:
            await elasticsearch_service.close()

    def _load_scorecard_weights(self):
        """Load scorecard weights for specialties."""
        file_path = self.data_dir / "scorecardweights.csv"
        if not file_path.exists():
            logger.warning(f"Scorecard weights file not found: {file_path}")
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.scorecards[row['name']] = {
                    'id': int(row['id']),
                    'weights': json.loads(row['weights']) if row['weights'] else {},
                    'version': row['version']
                }
        logger.info(f"Loaded {len(self.scorecards)} scorecard definitions")

    def _load_normalized_mapping(self):
        """Load lawyer normalization mapping."""
        file_path = self.data_dir / "lawyer_normalized_mapping.csv"
        if not file_path.exists():
            logger.warning(f"Normalized mapping file not found: {file_path}")
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                lawyer_id = int(row['lawyer_id'])
                normalized_id = int(row['normalized_name_id'])
                self.normalized_mapping[lawyer_id] = normalized_id
        logger.info(f"Loaded {len(self.normalized_mapping)} normalization mappings")

    def _load_merged_lawyers(self):
        """Load merged lawyer data."""
        file_path = self.data_dir / "merged_lawyers.csv"
        if not file_path.exists():
            logger.warning(f"Merged lawyers file not found: {file_path}")
            return

        # Use pandas for better handling of complex fields
        df = pd.read_csv(file_path)
        df = df.where(pd.notna(df), None)  # Replace NaN with None

        for _, row in df.iterrows():
            lawyer_id = int(row['id'])
            self.merged_lawyers[lawyer_id] = {
                'id': lawyer_id,
                'name': row['name'],
                'city': row['city'],
                'state': row['state'],
                'profile_phones': self._parse_json_field(row.get('profile_phones')),
                'payment_methods': self._parse_json_field(row.get('payment_methods')),
                'languages': self._parse_json_field(row.get('languages')),
                'categories': self._parse_json_field(row.get('categories')),
                'full_categories': self._parse_json_field(row.get('full_categories')),
                'gender': row.get('gender'),
                'education': row.get('education'),
                'professional_experience': row.get('professional_experience'),
                'awards': row.get('awards'),
                'associations': row.get('associations'),
                'profile_summary': row.get('profile_summary'),
                'perplexity_score': float(row['perplexity_score']) if row.get('perplexity_score') else None,
                'perplexity_review': row.get('perplexity_review')
            }
        logger.info(f"Loaded {len(self.merged_lawyers)} merged lawyers")

    def _load_locations(self):
        """Load lawyer location data."""
        file_path = self.data_dir / "merged_lawyers_locations.csv"
        if not file_path.exists():
            logger.warning(f"Locations file not found: {file_path}")
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                lawyer_id = int(row['merged_lawyers_id'])
                coord = row['coordinate']

                # Parse POINT format
                if coord and 'POINT' in coord:
                    import re
                    match = re.match(r'POINT \(([-\d.]+) ([-\d.]+)\)', coord)
                    if match:
                        self.locations[lawyer_id] = {
                            'lat': float(match.group(2)),
                            'lon': float(match.group(1))
                        }
        logger.info(f"Loaded {len(self.locations)} lawyer locations")

    def _load_source_data(self):
        """Load lawyer source data with licenses and ratings."""
        file_path = self.data_dir / "merged_lawyers_source_data.csv"
        if not file_path.exists():
            logger.warning(f"Source data file not found: {file_path}")
            return

        df = pd.read_csv(file_path)
        df = df.where(pd.notna(df), None)

        for _, row in df.iterrows():
            lawyer_id = int(row['merged_lawyers_id'])
            source = row['source']

            if lawyer_id not in self.source_data:
                self.source_data[lawyer_id] = {}

            self.source_data[lawyer_id][source] = {
                'lawyer_id': int(row['lawyer_id']),
                'avatar': row.get('avatar'),
                'badge': self._parse_json_field(row.get('badge')),
                'barcodes': self._parse_json_field(row.get('barcodes')),
                'rating': float(row['rating']) if row.get('rating') else None,
                'link': row.get('link'),
                'licenses': self._parse_json_field(row.get('licenses')),
                'has_license': row.get('has_license'),
                'geocoded_addresses': self._parse_json_field(row.get('geocoded_addresses'))
            }
        logger.info(f"Loaded source data for {len(self.source_data)} lawyers")

    def _load_reviews(self):
        """Load Google Places reviews."""
        file_path = self.data_dir / "googleplacesreview.csv"
        if not file_path.exists():
            logger.warning(f"Reviews file not found: {file_path}")
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                lawyer_id = int(row['lawyer_id'])

                # Get normalized ID
                normalized_id = self.normalized_mapping.get(lawyer_id, lawyer_id)

                if normalized_id not in self.reviews:
                    self.reviews[normalized_id] = []

                if row.get('reviews'):
                    review_data = self._parse_json_field(row['reviews'])
                    if isinstance(review_data, dict):
                        self.reviews[normalized_id].append(review_data)
                    elif isinstance(review_data, list):
                        self.reviews[normalized_id].extend(review_data)

        logger.info(f"Loaded reviews for {len(self.reviews)} lawyers")

    def _transform_lawyers(self) -> List[Dict[str, Any]]:
        """Transform lawyer data into Elasticsearch format."""
        transformed_lawyers = []

        for lawyer_id, lawyer in self.merged_lawyers.items():
            doc = {
                'id': lawyer_id,
                'normalized_id': lawyer_id,  # Already normalized in merged_lawyers
                'name': lawyer['name'],
                'city': lawyer['city'],
                'state': lawyer['state'],
                'active': True,
                'last_updated': datetime.utcnow().isoformat()
            }

            # Location
            if lawyer_id in self.locations:
                doc['location'] = self.locations[lawyer_id]

            # Practice areas and specialties
            if lawyer.get('categories'):
                doc['practice_areas'] = lawyer['categories']
                doc['specialties'] = self._extract_specialties(lawyer)

            # Professional info
            for field in ['profile_summary', 'education', 'professional_experience',
                         'awards', 'associations']:
                if lawyer.get(field):
                    doc[field] = lawyer[field]

            # Contact info
            if lawyer.get('profile_phones'):
                doc['phone_numbers'] = lawyer['profile_phones']

            # Languages and payment
            if lawyer.get('languages'):
                doc['languages'] = lawyer['languages']
            if lawyer.get('payment_methods'):
                doc['payment_methods'] = lawyer['payment_methods']

            # Demographics
            if lawyer.get('gender'):
                doc['gender'] = lawyer['gender']

            # Ratings and quality scores
            doc['ratings'] = self._aggregate_ratings(lawyer_id)
            doc['quality_signals'] = self._calculate_quality_signals(lawyer)

            # Reviews
            if lawyer_id in self.reviews:
                doc['reviews'] = self._process_reviews(self.reviews[lawyer_id])

            # AI-generated content
            if lawyer.get('perplexity_score'):
                doc['perplexity_score'] = lawyer['perplexity_score']
            if lawyer.get('perplexity_review'):
                doc['perplexity_review'] = lawyer['perplexity_review']

            # Licenses and bar admissions
            doc['licenses'] = self._extract_licenses(lawyer_id)
            doc['years_of_experience'] = self._calculate_experience_years(doc['licenses'])

            # Profile URLs
            doc['profile_urls'] = self._extract_profile_urls(lawyer_id)

            # Scorecards
            doc['scorecards'] = self._calculate_scorecards(lawyer)

            transformed_lawyers.append(doc)

        return transformed_lawyers

    def _extract_specialties(self, lawyer: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract specialty information from categories."""
        specialties = []

        # Map categories to specialty structure
        category_mapping = {
            'divorce': {'category': 'divorce_separation', 'name': 'Divorce Law'},
            'custody': {'category': 'child_custody', 'name': 'Child Custody'},
            'child support': {'category': 'child_support', 'name': 'Child Support'},
            'adoption': {'category': 'adoption', 'name': 'Adoption Law'},
            'domestic violence': {'category': 'domestic_violence', 'name': 'Domestic Violence'},
            'property division': {'category': 'property_division', 'name': 'Property Division'},
            'alimony': {'category': 'alimony', 'name': 'Spousal Support'},
            'guardianship': {'category': 'guardianship', 'name': 'Guardianship'},
            'paternity': {'category': 'paternity', 'name': 'Paternity'},
            'juvenile': {'category': 'juvenile_dependency', 'name': 'Juvenile Law'}
        }

        categories = lawyer.get('categories', []) + lawyer.get('full_categories', [])
        seen = set()

        for cat in categories:
            if cat and isinstance(cat, str):
                cat_lower = cat.lower()
                for key, spec_info in category_mapping.items():
                    if key in cat_lower and spec_info['category'] not in seen:
                        specialties.append({
                            'name': spec_info['name'],
                            'category': spec_info['category'],
                            'subcategory': cat
                        })
                        seen.add(spec_info['category'])

        return specialties

    def _aggregate_ratings(self, lawyer_id: int) -> Dict[str, Any]:
        """Aggregate ratings from different sources."""
        ratings = {}

        # Google reviews rating
        if lawyer_id in self.reviews and self.reviews[lawyer_id]:
            google_ratings = [r.get('rating', 0) for r in self.reviews[lawyer_id] if r.get('rating')]
            if google_ratings:
                ratings['google'] = sum(google_ratings) / len(google_ratings)
                ratings['review_count'] = len(google_ratings)

        # Source platform ratings
        if lawyer_id in self.source_data:
            for source, data in self.source_data[lawyer_id].items():
                if data.get('rating'):
                    ratings[source] = data['rating']

        # Overall rating (average of all sources)
        all_ratings = [v for k, v in ratings.items() if k != 'review_count' and isinstance(v, (int, float))]
        if all_ratings:
            ratings['overall'] = sum(all_ratings) / len(all_ratings)

        return ratings

    def _calculate_quality_signals(self, lawyer: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate quality signal scores."""
        signals = {}

        # Education score (0-10)
        if lawyer.get('education'):
            signals['education_score'] = min(10, len(lawyer['education']) / 50)

        # Professional score based on experience
        if lawyer.get('professional_experience'):
            signals['professional_score'] = min(10, len(lawyer['professional_experience']) / 100)

        # Awards score
        if lawyer.get('awards'):
            signals['awards_score'] = min(10, lawyer['awards'].count(',') + 1)

        # Associations score
        if lawyer.get('associations'):
            signals['associations_score'] = min(10, lawyer['associations'].count(',') + 1)

        return signals

    def _process_reviews(self, reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and structure reviews."""
        processed = []

        for review in reviews:
            if isinstance(review, dict):
                processed.append({
                    'source': 'google',
                    'rating': review.get('rating'),
                    'text': review.get('text', ''),
                    'timestamp': review.get('timestamp')
                })

        return processed

    def _extract_licenses(self, lawyer_id: int) -> List[Dict[str, Any]]:
        """Extract license information from source data."""
        licenses = []

        if lawyer_id in self.source_data:
            for source, data in self.source_data[lawyer_id].items():
                if data.get('licenses'):
                    for license_info in data['licenses']:
                        if isinstance(license_info, dict):
                            licenses.append({
                                'state': license_info.get('jurisdiction', ''),
                                'status': license_info.get('status', 'unknown'),
                                'year_admitted': license_info.get('year_admitted'),
                                'duration_years': license_info.get('duration_years'),
                                'has_disciplinary_actions': bool(license_info.get('disciplinary_info'))
                            })

        return licenses

    def _calculate_experience_years(self, licenses: List[Dict[str, Any]]) -> Optional[float]:
        """Calculate years of experience from licenses."""
        if not licenses:
            return None

        years = [l.get('duration_years', 0) for l in licenses if l.get('duration_years')]
        return max(years) if years else None

    def _extract_profile_urls(self, lawyer_id: int) -> Dict[str, str]:
        """Extract profile URLs from source data."""
        urls = {}

        if lawyer_id in self.source_data:
            for source, data in self.source_data[lawyer_id].items():
                if data.get('link'):
                    urls[source] = data['link']

        return urls

    def _calculate_scorecards(self, lawyer: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Calculate scorecard scores for specialties."""
        scorecards = []

        # Get lawyer's specialties
        categories = set(lawyer.get('categories', []) + lawyer.get('full_categories', []))

        # Match with scorecard definitions
        for specialty, scorecard in self.scorecards.items():
            # Simple keyword matching - can be improved
            if any(specialty.lower() in cat.lower() for cat in categories if cat):
                scorecards.append({
                    'specialty': specialty,
                    'score': 7.5,  # Default score - should be calculated based on weights
                    'weights': scorecard['weights']
                })

        return scorecards

    def _parse_json_field(self, field_value: Any) -> Any:
        """Parse JSON fields from CSV."""
        if pd.isna(field_value) or field_value is None:
            return None

        if isinstance(field_value, str):
            try:
                # Handle escaped JSON
                if field_value.startswith('[') or field_value.startswith('{'):
                    return json.loads(field_value)
                elif field_value.startswith('"[') or field_value.startswith('"{'):
                    # Double-encoded JSON
                    return json.loads(json.loads(field_value))
            except:
                return field_value

        return field_value


async def main():
    """Main entry point for the data loader."""
    import argparse

    parser = argparse.ArgumentParser(description='Load lawyer data into Elasticsearch')
    parser.add_argument('--data-dir', default='./data', help='Directory containing CSV files')
    parser.add_argument('--clear-index', action='store_true', help='Clear existing index before loading')

    args = parser.parse_args()

    loader = LawyerDataLoader(data_dir=args.data_dir)

    if args.clear_index:
        logger.warning("Clearing existing index is not implemented yet")

    await loader.load_all_data()


if __name__ == "__main__":
    print("Loading lawyer data into Elasticsearch...")
    print("Make sure Elasticsearch is running and CSV files are in the data directory")
    print("-" * 50)

    asyncio.run(main())
