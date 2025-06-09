# LoveAndLaw Data Dictionary

This document describes the structure and content of each CSV file in the LoveAndLaw dataset, excluding `lawyer.csv` and `lawyer_cleaned.csv`.

## Table of Contents
- [LoveAndLaw Data Dictionary](#loveandlaw-data-dictionary)
  - [Table of Contents](#table-of-contents)
  - [googleplacesreview.csv](#googleplacesreviewcsv)
    - [Columns:](#columns)
    - [Example:](#example)
  - [lawyer\_normalized\_mapping.csv](#lawyer_normalized_mappingcsv)
    - [Columns:](#columns-1)
    - [Notes:](#notes)
  - [merged\_lawyers.csv](#merged_lawyerscsv)
    - [Columns:](#columns-2)
    - [Notes:](#notes-1)
  - [merged\_lawyers\_locations.csv](#merged_lawyers_locationscsv)
    - [Columns:](#columns-3)
    - [Example:](#example-1)
  - [merged\_lawyers\_source\_data.csv](#merged_lawyers_source_datacsv)
    - [Columns:](#columns-4)
  - [scorecardweights.csv](#scorecardweightscsv)
    - [Columns:](#columns-5)
    - [Family Law Specialties and Categories](#family-law-specialties-and-categories)
      - [1. Divorce \& Separation (53,433 lawyers)](#1-divorce--separation-53433-lawyers)
      - [2. Property Division (2,030 lawyers)](#2-property-division-2030-lawyers)
      - [3. Child Custody (20,627 lawyers)](#3-child-custody-20627-lawyers)
      - [4. Child Support (17,109 lawyers)](#4-child-support-17109-lawyers)
      - [5. Alimony/Spousal Support (5,016 lawyers)](#5-alimonyspousal-support-5016-lawyers)
      - [6. Domestic Violence (13,021 lawyers)](#6-domestic-violence-13021-lawyers)
      - [7. Protection Orders (202 lawyers)](#7-protection-orders-202-lawyers)
      - [8. Adoption (8,934 lawyers)](#8-adoption-8934-lawyers)
      - [9. Juvenile \& Dependency (8,227 lawyers)](#9-juvenile--dependency-8227-lawyers)
      - [10. Paternity (2,806 lawyers)](#10-paternity-2806-lawyers)
      - [11. Guardianship (3,552 lawyers)](#11-guardianship-3552-lawyers)
      - [12. Child Abuse \& Neglect (2,391 lawyers)](#12-child-abuse--neglect-2391-lawyers)
      - [Additional Specialties (Not in scorecardweights.csv):](#additional-specialties-not-in-scorecardweightscsv)
    - [Scoring System in scorecardweights.csv](#scoring-system-in-scorecardweightscsv)
      - [Specialty Scorecards:](#specialty-scorecards)
      - [Quality Signal Scorecards:](#quality-signal-scorecards)
    - [Example Weights:](#example-weights)
  - [Data Quality Notes](#data-quality-notes)

---

## googleplacesreview.csv
Contains Google Places reviews and ratings for lawyers.

### Columns:
- **id** (integer): Unique identifier for the review record
- **lawyer_id** (integer): References the lawyer in the source data
- **rating** (float): Google Places rating (1.0-5.0 scale), can be null
- **reviews** (JSON string): Array of review objects containing:
  - `rating`: Individual review rating
  - `text`: Review text content
  - `timestamp`: Unix timestamp of when review was posted

### Example:
```
id: 47965
lawyer_id: 31287
rating: 5.0
reviews: {"rating": 5, "text": "", "timestamp": 1650052934}
```

---

## lawyer_normalized_mapping.csv
Maps individual lawyer IDs to normalized (deduplicated) lawyer entities.

### Columns:
- **lawyer_id** (integer): Original lawyer ID from source data
- **normalized_name_id** (integer): ID of the deduplicated lawyer entity

### Notes:
- Multiple lawyer_ids can map to the same normalized_name_id
- This handles cases where the same lawyer appears in multiple data sources
- Total mappings: 133,716
- Unique normalized IDs: 123,454

---

## merged_lawyers.csv
Central table containing consolidated lawyer information after deduplication.

### Columns:
- **id** (integer): Unique identifier for the merged lawyer record
- **name** (string): Full name of the lawyer
- **city** (string): Primary city location
- **state** (string): State where lawyer practices
- **profile_phones** (array): Phone numbers in JSON format
- **payment_methods** (array): Accepted payment types
- **languages** (array): Languages spoken
- **bloglinks** (array): Links to blogs or articles
- **categories** (array): Primary practice categories
- **full_categories** (array): Complete list of practice areas
- **lawyer_ids** (array): Source lawyer IDs that were merged
- **gender** (string): Gender if available
- **education** (string): Educational background
- **professional_experience** (string): Work history
- **awards** (string): Professional awards and recognition
- **associations** (string): Professional associations
- **office** (string): Office information
- **profile_summary** (string): Professional summary
- **score_cards** (string): Performance scores
- **signals** (string): Quality indicators
- **embeddings** (string): Vector embeddings for ML
- **perplexity_score** (float): AI-generated quality score
- **perplexity_review** (string): AI-generated review

### Notes:
- 10,642 lawyers have multiple source IDs (merged from multiple platforms)

---

## merged_lawyers_locations.csv
Geographic coordinates for lawyer office locations.

### Columns:
- **id** (integer): Unique location record ID
- **merged_lawyers_id** (integer): References merged_lawyers.id
- **coordinate** (POINT): PostGIS geometry point (longitude, latitude)

### Example:
```
id: 1
merged_lawyers_id: 29156
coordinate: POINT (-118.417478 34.0572616)
```

---

## merged_lawyers_source_data.csv
Detailed source information for each merged lawyer from various platforms.

### Columns:
- **id** (integer): Unique source data record ID
- **merged_lawyers_id** (integer): References merged_lawyers.id
- **lawyer_id** (integer): Original source lawyer ID
- **source** (string): Data source platform (avvo, justia, findlaw)
- **avatar** (string): Profile image URL
- **badge** (array): Professional badges/certifications
- **barcodes** (array): Bar association codes
- **rating** (float): Platform-specific rating
- **link** (string): Profile URL on source platform
- **geocoded_addresses** (JSON): Detailed address information with:
  - Full geocoding data from Google Maps API
  - Formatted addresses
  - Location coordinates
  - Place IDs
- **licenses** (JSON array): License information containing:
  - `status`: Active/Inactive status
  - `jurisdiction`: State/jurisdiction
  - `year_admitted`: Year admitted to bar
  - `duration_years`: Years of practice
  - `disciplinary_info`: Any disciplinary actions
- **has_license** (string): License status (yes/no/unknown)

---

## scorecardweights.csv
Scoring criteria and weights for different family law specialties.

### Columns:
- **id** (integer): Scorecard ID
- **weights** (JSON): Key-value pairs of criteria and importance (0-10)
- **version** (string): Scorecard version number
- **name** (string): Specialty area name

### Family Law Specialties and Categories

Based on analysis of 128,660 unique lawyers in merged_lawyers.csv:

#### 1. Divorce & Separation (53,433 lawyers)
- **Subcategories**: Divorce, Uncontested Divorce, Contested Divorce, High-Asset Divorce, Military Divorce, Collaborative Divorce, Divorce Mediation, Legal Separation, Annulment
- **Not in scorecards**: Military Divorce (1,291), Uncontested Divorce (2,138), Collaborative Divorce (1,806)

#### 2. Property Division (2,030 lawyers)
- **Subcategories**: Property Division, Asset Division, Debt Division, Business Valuation, Hidden Assets, Pension Division, Real Estate Division

#### 3. Child Custody (20,627 lawyers)
- **Subcategories**: Child Custody, Joint Custody, Sole Custody, Physical Custody, Legal Custody, Custody Modifications, Custody Disputes, Parenting Plans, Custody & Visitation

#### 4. Child Support (17,109 lawyers)
- **Subcategories**: Child Support, Support Calculations, Support Modifications, Support Enforcement, Child Support & Paternity, Interstate Support, Medical Support

#### 5. Alimony/Spousal Support (5,016 lawyers)
- **Subcategories**: Alimony, Spousal Support, Temporary Alimony, Permanent Alimony, Rehabilitative Alimony, Spousal Maintenance, Support Modifications

#### 6. Domestic Violence (13,021 lawyers)
- **Subcategories**: Domestic Violence, Domestic Abuse, Family Violence, Spousal Abuse, Child & Spousal Abuse, Elder Abuse, Emergency Protection

#### 7. Protection Orders (202 lawyers)
- **Subcategories**: Restraining Orders, Protection Orders, Orders of Protection, Emergency Orders, Civil Protection Orders, No-Contact Orders

#### 8. Adoption (8,934 lawyers)
- **Subcategories**: Adoption, International Adoption, Domestic Adoption, Stepparent Adoption, Adult Adoption, Same-Sex Adoption, Foster Care Adoption, Open/Closed Adoption

#### 9. Juvenile & Dependency (8,227 lawyers)
- **Subcategories**: Juvenile Law, Juvenile Dependency, Juvenile Delinquency, CHIPS Cases, TPR (Termination of Parental Rights), Foster Care Law

#### 10. Paternity (2,806 lawyers)
- **Subcategories**: Paternity Actions, Paternity Disputes, Fathers' Rights, Mothers' Rights, Parentage, Legitimation, Paternity Testing, Disestablishment of Paternity

#### 11. Guardianship (3,552 lawyers)
- **Subcategories**: Adult Guardianship, Minor Guardianship, Guardian Ad Litem, Conservatorships, Emergency Guardianship, Probate Guardianship, Guardian Advocate, Incapacitation

#### 12. Child Abuse & Neglect (2,391 lawyers)
- **Subcategories**: Child Abuse, Child Neglect, Child Protection, CPS Cases, Child Welfare, Dependency Proceedings, Child Abuse Defense

#### Additional Specialties (Not in scorecardweights.csv):
- **Prenuptial Agreements** (4,951 lawyers): Prenups, Postnuptial Agreements, Marriage Contracts
- **Visitation Rights** (744 lawyers): Visitation Schedules, Grandparent Rights, Third-Party Visitation
- **LGBT+ Family Law** (1,508 lawyers): Same-Sex Divorce, Same-Sex Adoption, LGBT+ Custody Issues

### Scoring System in scorecardweights.csv

The scoring system uses weighted criteria (0-10 scale) for each specialty area:

#### Specialty Scorecards:
1. **divorce_separation_general** - Covers all divorce and separation matters
2. **property_division_general** - Asset and debt division expertise
3. **child_custody_general** - All custody-related matters
4. **child_support_general** - Support calculation and enforcement
5. **alimony_general** - Spousal support expertise
6. **domestic_violence_general** - DV case handling
7. **restraining_orders_general** - Protection order expertise
8. **adoption_general** - All adoption types
9. **juvenile_dependency_general** - Juvenile court matters
10. **paternity_general** - Parentage establishment
11. **guardianship_general** - All guardianship types
12. **child_abuse_general** - Child protection cases

#### Quality Signal Scorecards:
13. **signal_education** - Education quality indicators
14. **signal_professional** - Professional experience signals
15. **signal_awards** - Awards and recognition signals
16. **signal_associations** - Professional association signals

Note: The "_general" suffix indicates broad scoring criteria encompassing all subcategories within that specialty.

### Example Weights:
```json
{
  "Divorce Law Experience": 10,
  "Fee Structure Transparency": 9,
  "Negotiation/Mediation Skills": 8,
  "Local Court Experience": 8
}
```

---

## Data Quality Notes

1. **Missing Data**: Many fields can be null or empty, particularly:
   - Google reviews (many lawyers have no reviews)
   - Professional details (education, experience)
   - Demographic information

2. **Data Sources**: Information comes from multiple platforms:
   - Avvo (lawyer ratings and profiles)
   - Justia (legal directory)
   - FindLaw (attorney listings)
   - Google Places (reviews and ratings)

3. **Deduplication**: The normalized mapping handles:
   - Same lawyer on multiple platforms
   - Name variations
   - Multiple office locations

4. **Geographic Coverage**: Primarily US-based lawyers with focus on family law practitioners
