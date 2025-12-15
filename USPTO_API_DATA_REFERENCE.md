# USPTO Open Data Portal (ODP) API - Complete Data Reference

**Base URL:** `https://api.uspto.gov/api/v1`
**Authentication:** `X-API-Key` header
**Documentation:** https://data.uspto.gov/swagger/index.html

---

## API Endpoints

### Patent File Wrapper APIs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/patent/applications/search` | GET/POST | Search patent applications |
| `/patent/applications/search/download` | GET/POST | Download search results (JSON/CSV) |
| `/patent/applications/{appNum}` | GET | Full application data |
| `/patent/applications/{appNum}/meta-data` | GET | Application metadata only |
| `/patent/applications/{appNum}/transactions` | GET | Transaction/event history |
| `/patent/applications/{appNum}/documents` | GET | Document list with download URLs |
| `/patent/applications/{appNum}/continuity` | GET | Parent/child relationships |
| `/patent/applications/{appNum}/assignment` | GET | Ownership/assignment records |
| `/patent/applications/{appNum}/attorney` | GET | Attorney/agent information |
| `/patent/applications/{appNum}/adjustment` | GET | Patent term adjustment (PTA) |
| `/patent/applications/{appNum}/foreign-priority` | GET | Foreign priority claims |
| `/patent/applications/{appNum}/associated-documents` | GET | PGPub/Grant document metadata |
| `/patent/status-codes` | GET/POST | Status code lookup |

### PTAB APIs

| Endpoint | Description |
|----------|-------------|
| `/patent/trials/proceedings/search` | PTAB trial proceedings |
| `/patent/trials/decisions/search` | PTAB trial decisions |
| `/patent/trials/documents/search` | PTAB trial documents |
| `/patent/appeals/decisions/search` | PTAB appeal decisions |
| `/patent/interferences/decisions/search` | PTAB interference decisions |

### Other APIs

| Endpoint | Description |
|----------|-------------|
| `/petition/decisions/search` | Petition decision search |
| `/datasets/products/search` | Bulk dataset search |
| `/datasets/products/{id}` | Bulk dataset details |
| `/datasets/products/files/{id}/{file}` | Bulk data file download |

---

## Complete Data Schemas

### ApplicationMetaData

Core patent application metadata fields.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `nationalStageIndicator` | boolean | Whether app entered national stage from PCT | `true` |
| `filingDate` | date | Filing date (INID Code 22) | `2012-12-19` |
| `effectiveFilingDate` | date | Effective filing date per PTO criteria | `2013-12-12` |
| `grantDate` | date | Patent grant date | `2016-06-07` |
| `applicationStatusDate` | date | Date of current status | `2016-05-18` |
| `applicationStatusCode` | integer | Status code number | `150` |
| `applicationStatusDescriptionText` | string | Status description | `Patented Case` |
| `applicationTypeCode` | string | Type code (UTL/DES/PLT/REI) | `UTL` |
| `applicationTypeLabelName` | string | Type name | `Utility` |
| `applicationTypeCategory` | string | Category | `electronics` |
| `inventionTitle` | string | Invention title | `HETEROJUNCTION BIPOLAR TRANSISTOR` |
| `patentNumber` | string | Issued patent number | `9362380` |
| `docketNumber` | string | Attorney docket number | `12GR10425US01/859063.688` |
| `applicationConfirmationNumber` | number | Confirmation number | `1061` |
| `firstInventorToFileIndicator` | string | First inventor to file? | `Y` |
| `firstApplicantName` | string | First applicant name | `STMicroelectronics S.A.` |
| `firstInventorName` | string | First inventor name | `Pascal Chevalier` |
| `examinerNameText` | string | Examiner name | `HUI TSAI JEY` |
| `groupArtUnitNumber` | string | Art unit (GAU) | `2816` |
| `customerNumber` | integer | Customer number | `38106` |
| `class` | string | USPC class | `257` |
| `subclass` | string | USPC subclass | `197000` |
| `uspcSymbolText` | string | Full USPC classification | `257/197000` |
| `cpcClassificationBag` | array | CPC classifications | `["H01L29/66325", "H01L27/0623"]` |
| `earliestPublicationNumber` | string | First publication number | `US 2014-0167116 A1` |
| `earliestPublicationDate` | date | First publication date | `2014-06-19` |
| `publicationDateBag` | array | All publication dates | `["2014-06-19"]` |
| `publicationSequenceNumberBag` | array | Publication sequence numbers | `["0167116"]` |
| `publicationCategoryBag` | array | Publication categories | `["Granted/Issued", "Pre-Grant Publications"]` |
| `pctPublicationNumber` | string | PCT publication number | `WO 2009/064413` |
| `pctPublicationDate` | date | PCT publication date | `2016-12-16` |
| `internationalRegistrationNumber` | string | Intl registration number | `DM/091304` |
| `internationalRegistrationPublicationDate` | date | Intl registration pub date | `2016-12-16` |

#### entityStatusData (nested in ApplicationMetaData)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `smallEntityStatusIndicator` | boolean | Qualifies for small entity | `true` |
| `businessEntityStatusCategory` | string | Entity status | `Small`, `Micro`, `Undiscounted` |

#### applicantBag (array in ApplicationMetaData)

| Field | Type | Description |
|-------|------|-------------|
| `applicantNameText` | string | Full applicant name |
| `firstName` | string | First name |
| `middleName` | string | Middle name |
| `lastName` | string | Last name |
| `preferredName` | string | Preferred name |
| `namePrefix` | string | Prefix (Mr., Dr., etc.) |
| `nameSuffix` | string | Suffix (Jr., Sr., etc.) |
| `countryCode` | string | Country code |
| `correspondenceAddressBag` | array | Applicant addresses |

#### inventorBag (array in ApplicationMetaData)

| Field | Type | Description |
|-------|------|-------------|
| `inventorNameText` | string | Full inventor name |
| `firstName` | string | First name |
| `middleName` | string | Middle name |
| `lastName` | string | Last name |
| `preferredName` | string | Preferred name |
| `namePrefix` | string | Prefix |
| `nameSuffix` | string | Suffix |
| `countryCode` | string | Country code |
| `correspondenceAddressBag` | array | Inventor addresses |

---

### EventData (Transactions/History)

Transaction history for the application. **This is what the Patent Status Tracker monitors.**

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `eventCode` | string | Event code | `CTNF`, `NOA`, `WIDS`, `BRCE` |
| `eventDescriptionText` | string | Event description | `Non-Final Rejection`, `Notice of Allowance` |
| `eventDate` | date | Date event occurred | `2018-10-18` |

**Common Event Codes:**
- `CTNF` - Non-Final Rejection
- `CTFR` - Final Rejection
- `NOA` - Notice of Allowance
- `MCTNF` - Mail Non-Final Rejection
- `MCTFR` - Mail Final Rejection
- `WIDS` - IDS Filed
- `IDSC` - IDS Considered
- `BRCE` - RCE Begin
- `RCE` - Request for Continued Examination
- `RESP` - Response Filed
- `OIPE` - Office Action Entry
- `DOCK` - Docketed New Case
- `EML_NTF` - Email Notification
- `ELC_RVW` - Electronic Review

---

### Assignment (Ownership Records)

Patent assignment/ownership data.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `reelNumber` | string | Microfilm reel number | `60620` |
| `frameNumber` | string | Microfilm frame number | `769` |
| `reelAndFrameNumber` | string | Combined reel/frame | `60620/769` |
| `pageTotalQuantity` | integer | Number of pages | `16` |
| `imageAvailableStatusCode` | boolean | Image available | `false` |
| `assignmentDocumentLocationURI` | string | Document URL | `https://legacy-assignments.uspto.gov/...` |
| `assignmentReceivedDate` | date | Date received | `2022-07-11` |
| `assignmentRecordedDate` | date | Date recorded | `2022-07-11` |
| `assignmentMailedDate` | date | Date mailed | `2022-07-28` |
| `conveyanceText` | string | Nature of conveyance | `ASSIGNMENT OF ASSIGNORS INTEREST` |

#### assignorBag (array)

| Field | Type | Description |
|-------|------|-------------|
| `assignorName` | string | Assignor name |
| `executionDate` | date | Execution date |

#### assigneeBag (array)

| Field | Type | Description |
|-------|------|-------------|
| `assigneeNameText` | string | Assignee name |
| `assigneeAddress` | object | Address details |

---

### PatentTermAdjustment

Patent term adjustment (PTA) data for calculating patent expiration.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `adjustmentTotalQuantity` | integer | Total PTA days | `0` |
| `aDelayQuantity` | integer | A delays (USPTO delays) | `0` |
| `bDelayQuantity` | integer | B delays (3-year issue deadline) | `0` |
| `cDelayQuantity` | integer | C delays (interference/secrecy/appeals) | `0` |
| `applicantDayDelayQuantity` | integer | Applicant delays | `28` |
| `nonOverlappingDayQuantity` | float | Non-overlapping USPTO delays | `0` |
| `overlappingDayQuantity` | float | Overlapping delays | `0` |
| `patentTermAdjustmentHistoryDataBag` | array | PTA history events |

#### patentTermAdjustmentHistoryDataBag (array)

| Field | Type | Description |
|-------|------|-------------|
| `eventDate` | date | Event date |
| `eventDescriptionText` | string | Event description |
| `eventSequenceNumber` | float | Sequence number |
| `applicantDayDelayQuantity` | integer | Applicant delay days |
| `ipOfficeDayDelayQuantity` | integer | USPTO delay days |
| `originatingEventSequenceNumber` | float | Originating event |
| `ptaPTECode` | string | PTA/PTE code |

---

### ParentContinuityData

Parent application continuity data.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `parentApplicationNumberText` | string | Parent app number | `123123133` |
| `childApplicationNumberText` | string | Child app number | `10121016` |
| `parentApplicationFilingDate` | date | Parent filing date | `2012-05-23` |
| `parentPatentNumber` | string | Parent patent number | `8968299` |
| `parentApplicationStatusCode` | integer | Parent status code | `159` |
| `parentApplicationStatusDescriptionText` | string | Parent status | `Patent Expired...` |
| `claimParentageTypeCode` | string | Relationship type code | `CON`, `DIV`, `CIP` |
| `claimParentageTypeCodeDescriptionText` | string | Relationship description | `Claims priority from provisional` |
| `firstInventorToFileIndicator` | boolean | First inventor to file | `true` |

---

### ChildContinuityData

Child application continuity data.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `parentApplicationNumberText` | string | Parent app number | `14104993` |
| `childApplicationNumberText` | string | Child app number | `14853719` |
| `childApplicationFilingDate` | date | Child filing date | `2015-09-14` |
| `childPatentNumber` | string | Child patent number | `9704967` |
| `childApplicationStatusCode` | number | Child status code | `150` |
| `childApplicationStatusDescriptionText` | string | Child status | `Patented Case` |
| `claimParentageTypeCode` | string | Relationship type | `DIV` |
| `claimParentageTypeCodeDescriptionText` | string | Relationship description |
| `firstInventorToFileIndicator` | boolean | First inventor to file | `false` |

---

### ForeignPriority

Foreign priority claims.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `ipOfficeName` | string | Foreign patent office | `FRANCE` |
| `filingDate` | date | Foreign filing date | `2012-12-19` |
| `applicationNumberText` | string | Foreign app number | `1262321` |

---

### RecordAttorney

Attorney/agent of record information.

#### customerNumberCorrespondenceData

| Field | Type | Description |
|-------|------|-------------|
| `patronIdentifier` | number | Customer number |
| `organizationStandardName` | string | Organization name |
| `powerOfAttorneyAddressBag` | array | POA addresses |
| `telecommunicationAddressBag` | array | Phone/fax numbers |

#### powerOfAttorneyBag (array)

| Field | Type | Description |
|-------|------|-------------|
| `firstName` | string | First name |
| `middleName` | string | Middle name |
| `lastName` | string | Last name |
| `namePrefix` | string | Prefix |
| `nameSuffix` | string | Suffix |
| `preferredName` | string | Preferred name |
| `countryCode` | string | Country |
| `registrationNumber` | string | USPTO reg number |
| `activeIndicator` | string | Active status |
| `registeredPractitionerCategory` | string | ATTNY or AGENT |
| `attorneyAddressBag` | array | Addresses |
| `telecommunicationAddressBag` | array | Phone numbers |

---

### DocumentBag (File Wrapper Documents)

Documents in the application file wrapper.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `applicationNumberText` | string | Application number | `16123123` |
| `officialDate` | string | Document date | `2020-08-31T01:20:29.000-0400` |
| `documentIdentifier` | string | Unique document ID | `LDXBTPQ7XBLUEX3` |
| `documentCode` | string | Document type code | `WFEE`, `CTNF`, `NOA` |
| `documentCodeDescriptionText` | string | Document description | `Fee Worksheet (SB06)` |
| `documentDirectionCategory` | string | Direction | `INTERNAL`, `INCOMING`, `OUTGOING` |

#### downloadOptionBag (array)

| Field | Type | Description |
|-------|------|-------------|
| `mimeTypeIdentifier` | string | File format (PDF, XML, DOCX) |
| `downloadUrl` | string | Download URL |
| `pageTotalQuantity` | integer | Page count |

**Common Document Codes:**
- `CTNF` - Non-Final Rejection
- `CTFR` - Final Rejection
- `NOA` - Notice of Allowance
- `WIDS` - IDS Transmittal
- `WFEE` - Fee Worksheet
- `CLM` - Claims
- `SPEC` - Specification
- `DRW` - Drawings
- `OATH` - Oath/Declaration
- `SRFW` - Search Report
- `SRNT` - Search Notes
- `892` - Examiner References Cited

---

### PGPubFileMetaData

Pre-grant publication document metadata.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `zipFileName` | string | Bulk data ZIP file | `ipa240801.zip` |
| `productIdentifier` | string | Product ID | `APPXML` |
| `fileLocationURI` | string | Download URL | `https://bulkdata.uspto.gov/...` |
| `fileCreateDateTime` | string | File creation time | `2024-08-09:11:30:00` |
| `xmlFileName` | string | XML file name | `ipa240801.xml` |

---

### GrantFileMetaData

Patent grant document metadata.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `zipFileName` | string | Bulk data ZIP file | `ipg240102.zip` |
| `productIdentifier` | string | Product ID | `PTGRXML` |
| `fileLocationURI` | string | Download URL | `https://bulkdata.uspto.gov/...` |
| `fileCreateDateTime` | string | File creation time | `2024-08-09:11:30:00` |
| `xmlFileName` | string | XML file name | `ipg160405.xml` |

---

### correspondenceAddressBag

Address information (used in multiple schemas).

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `nameLineOneText` | string | Name line 1 | `Seed IP Law Group LLP` |
| `nameLineTwoText` | string | Name line 2 | `Attn- IP Docket` |
| `addressLineOneText` | string | Address line 1 | `701 FIFTH AVENUE, SUITE 5400` |
| `addressLineTwoText` | string | Address line 2 | `Suite 501` |
| `cityName` | string | City | `SEATTLE` |
| `geographicRegionName` | string | State/region name | `WASHINGTON` |
| `geographicRegionCode` | string | State/region code | `WA` |
| `postalCode` | string | ZIP/postal code | `98104-7092` |
| `countryCode` | string | Country code | `US` |
| `countryName` | string | Country name | `USA` |
| `postalAddressCategory` | string | Address type | `commercial` |

---

## Search Query Syntax

The API supports OpenSearch query syntax:

| Operator | Example | Description |
|----------|---------|-------------|
| `AND` | `Utility AND Design` | Both terms required |
| `OR` | `Mark OR Design` | Either term |
| `NOT` | `Utility NOT Design` | Exclude term |
| `*` | `Rockwel*` | Wildcard |
| `""` | `"exact phrase"` | Exact phrase |
| `:` | `applicationStatusCode:150` | Field search |
| `[]` | `filingDate:[2021-08-04 TO 2021-09-04]` | Range search |
| `>` `<` | `applicationStatusCode:>600` | Comparison |

### Example Queries

```bash
# Search by application number
curl -X GET "https://api.uspto.gov/api/v1/patent/applications/14412875" \
  -H "X-API-KEY: YOUR_KEY"

# Search by inventor
curl -X GET "https://api.uspto.gov/api/v1/patent/applications/search?q=applicationMetaData.inventorBag.inventorNameText:Smith" \
  -H "X-API-KEY: YOUR_KEY"

# Search by filing date range
curl -X GET "https://api.uspto.gov/api/v1/patent/applications/search?q=applicationMetaData.filingDate:[2023-01-01 TO 2023-12-31]" \
  -H "X-API-KEY: YOUR_KEY"

# Get transactions/events
curl -X GET "https://api.uspto.gov/api/v1/patent/applications/17940142/transactions" \
  -H "X-API-KEY: YOUR_KEY"

# Get documents
curl -X GET "https://api.uspto.gov/api/v1/patent/applications/17940142/documents" \
  -H "X-API-KEY: YOUR_KEY"
```

---

## Rate Limits

See https://data.uspto.gov/apis/api-rate-limits for current limits.

---

## Notes

- **No webhooks available** - polling required for updates
- All dates in `yyyy-MM-dd` format
- Response payload limit: 6MB
- Default pagination: 25 records
- API key required for all endpoints
