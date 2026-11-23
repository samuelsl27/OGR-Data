# Material database sources (spec 010)

Tables transcribed from open official reports for the built-in records of
the OGR-Data material database. The original PDFs are kept (not in this
repository) in `Data/Referencias/Bibliografia/Bases_de_datos/`.

## CANMET 1995 — `canmet_1995_table1.csv`, `_table2.csv`, `_table3.csv`

Jackson, R., Gorski, B. & Gyenge, M. (1995). *Geotechnical Properties of
Rock*. CANMET, Natural Resources Canada (Government of Canada). Obtained
from the NRCan Open S&T Repository (OSTR), GID 331509,
<https://ostrnrcan-dostrncan.canada.ca/handle/1845/135598>.

- Table 1 "Physical Rock Properties" (p. 95-102 of the report, PDF pages
  102-109): 77 rows. Table 2 "Hoek and Brown Material Constants" (PDF
  pages 110-117): 77 rows. Table 3 "List of MRL reports": 31 references.
- Method: the report is a scanned document with a noisy OCR layer. Each
  table was transcribed value by value from page images rendered at
  2.2x, re-read twice, and compared with the OCR text. Tables 1 and 2
  were transcribed independently and cross-checked on their shared
  columns (rock, origin, reference, sigma_t, Qu).
- Discrepancies found are **in the source** (verified on the page
  images) and kept as printed; the importer reports them in the record
  notes:
  - sigma_t: limestone (fine-grained) 16/17 −9.41 (Table 1) vs −9.40
    (Table 2); sulphide iron 23/60 −27.90 vs −7.73.
  - Qu: mafic flow 5/20 316.91 vs 319.91; one value printed with one
    decimal in Table 2 (160.7 vs 160.76).
  - Table 2 prints limestone (bituminous) as data sheet "16/6"; Table 1
    and Table 3 give 16/16.
  - Table 1: "siltsone" (typo); diorite 24/53 density cell reads
    "10.00 −30.00" (a stress range, no density): left empty.
- sigma_t is printed negative (tension); the records store its magnitude.

## MnDOT 2018 — `mndot_2018_borings.csv`, `_ucs.csv`, `_triaxial.csv`, `_context.md`

Folta, B., Sharpe, J., Hu, C. & Labuz, J. (2018). *Development of a Rock
Strength Database*. Minnesota Department of Transportation, report
MN/RC 2018-19 (University of Minnesota). Distribution: "No restrictions".
<http://mndot.gov/research/reports/2018/201819.pdf> (copy from the
National Transportation Library, ROSA P, dot:36572).

- Tables 4.1 (borings), 4.2-4.4 (134 uniaxial specimens, SI units),
  5.1-5.4 (29 triaxial specimens with tabulated results).
- Method: PDF text layer in table layout, checked against page images,
  against the US-unit Tables 4.5-4.7, against area = πD²/4 and
  density = M/(A·L), and E against the Appendix A plots (130 of 131
  within 6 %).
- Context, lithology, test standards and the inconsistencies of the
  report (specimen 120, depth intervals, group 3 friction angle, table
  labels) are in `mndot_2018_context.md`. Not stated in the report and
  therefore NOT filled: the lithology of the TH 53 cores, the location of
  the triaxial projects and the coordinate system of Table 4.1 (no
  latitude/longitude is derived).

## Discarded / pending sources

- BGS datasets under the Open Government Licence (e.g. Sidmouth Mudstone
  Formation, doi:10.5285/1a95d3fa-3421-4d8a-a0eb-2aa756983c29): download
  through the NGDC web application with licence acceptance; not automated.
- DTIC AD0646610, USACE EM 1110-2-1906, FHWA NHI manuals: the servers
  refuse automated downloads (403); not forced.
- RocProp (Rocscience): proprietary, never used.
