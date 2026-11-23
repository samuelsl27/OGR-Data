# Context: Folta, Sharpe, Hu & Labuz (2018), "Development of a Rock Strength Database", MnDOT report MN/RC 2018-19

Source: Minnesota Department of Transportation Research Report MN/RC 2018-19, June 2018. Prepared by the Department of Civil, Environmental, and Geo- Engineering, University of Minnesota (PI Joseph Labuz). It has 233 pages.
Page references are given as "report page / PDF page". The PDF page is the report page + 10 for the main body. Quotes are verbatim, including the report's typos.

Abstract (p. ii): "The report provides a comprehensive suite of results from 134 specimens tested under uniaxial compression and 33 specimens tested under triaxial compression on a wide variety of rock, including hard rock..."

---

## Common to all data sets

### Test standards (Sec. 3.3, p. 11 / PDF 21)
> "The specimens were prepared in accordance to ASTM standards: Standard Test Method for Laboratory Determination of Pulse Velocities and Ultrasonic Elastic Constants of Rock, ASTM D2845; Standard Test Method for Unconfined Compressive Strength of Intact Rock Core Specimens, ASTM D2938; Standard Test Method for Elastic Moduli of Intact Rock Core Specimens in Uniaxial Compression, ASTM D3148; Standard Test Method for Triaxial Compressive Strength of Undrained Rock Core Specimens Without Pore Pressure Measurements, ASTM D2664."

- ASTM numbers: **D2845, D2938, D3148, D2664**. No edition years are given.
- Equipment: MTS 815 Rock Mechanics Test System, MTS Model 315.04 load frame with 4,600 kN capacity (Sec. 3.1, p. 7).
- The report states that the 2:1 L:D ratio "was not strictly enforced; i.e. L:D < 2 for a few UCS tests" (p. 11).
- A stearic acid lubricant was used to reduce end friction (p. 12).

### How UCS and E were determined (Sec. 3.4.4, p. 14 / PDF 24)
> "To calculate UCS, peak load is divided by the original cross sectional area; strictly speaking, the current area at peak load should be used but because the displacements are very small, the original area provides an accurate value. Young's modulus is determined from the slope of the axial stress-strain plot at the range corresponding to 30-50% of the UCS (Figure 3.10). Axial strain is calculated using the axial extensometer or the corrected axial displacement from the stroke."

- E is therefore a **tangent/secant-type slope from a linear fit over 30-50 % of UCS**.
- Appendix A has one plot per specimen (Figure A.x, "Young's modulus calculation"). Each plot shows the linear regression, for example Specimen 1: "y = 6.7984x + 41.772" with strain in E-04, which gives 67.98 GPa (the table gives 68.0).
- The report does not say which specimens used the extensometer and which used the corrected stroke.
- Axial extensometer gauge length: 50.0 mm, calibrated on a 6061 aluminium specimen with E = 69.0 GPa (Sec. 3.2.2, p. 9).
- Loading (Sec. 4.1, p. 15): "Stroke control was used ... For hard rock, such as the specimens provided from TH 53, the rate was 1-3 microns/s"; tests were completed within 5-10 min.
- Vp was measured from the P-wave travel time through the specimen length, read to the nearest 0.1 µs (p. 13, 15).
- Triaxial (Sec. 5.1, p. 23 / PDF 33):
  - "Failure was determined from the peak load and the original cross-sectional area of the specimens."
  - Axial displacement came from stroke, corrected for machine displacement using an aluminium specimen.
  - Friction angles in Table 5.4 are Mohr-Coulomb fits of sigma1 vs sigma3 per group (Figures 5.3-5.6 show linear fits y = N x + C0).

---

## Data set 1: TH 53 cores (Chapter 4; Tables 4.1-4.4, uniaxial, 134 specimens)

- **Project name:** TH 53 (Trunk Highway 53) project.
  - Sec. 4.1, p. 15 / PDF 25: "Rock cores were received from MnDOT from the TH 53 project, which requires relocation of the highway from its existing alignment due to the expiration of a 1960 easement and the subsequent planned expansion of the United Taconite Thunderbird Mine."
- **Location (county/city/state):**
  - State: Minnesota.
  - County and city: **not stated** in the report.
  - The only location descriptor is the reference to the United Taconite Thunderbird Mine, quoted above.
  - Chapter 6 (p. 29 / PDF 39) says "A bridge project in northern Minnesota provided an opportunity to expand the rock strength database", but it does not explicitly name TH 53.
- **Rock type / lithology / formation:** **not stated.**
  - The report only characterises the material as "hard rock" (p. 13 and p. 15: "For hard rock, such as the specimens provided from TH 53, the rate was 1-3 microns/s.").
  - No rock name, formation or lithology appears in Chapter 4, Tables 4.1-4.7, or the Appendix A specimen pages.
  - Sec. 4.3 (p. 22) only gives the Deere & Miller (1966) classification: "Most of the tested rock is in the very high (A) to medium (C) strength range with an average modulus ratio."
- **Specimen size:** nominal 50 mm diameter, L:D about 2.
  - Sec. 4.1: "Specimens were cut to a ratio of 2:1 (length:diameter) with a tolerance of 5 mm (0.20 in.)."
  - Results appear in SI units in Tables 4.2-4.4 and in US customary units in Tables 4.5-4.7 (same data).

### Table 4.1 "Rock boring metadata and locations" (p. 15 / PDF 25)
- **Columns:** Point ID, Unique Number, Hole Depth, Elevation, CC North (Y), CC East (X), UTM_N, UTM_E.
- **Units of Hole Depth and Elevation:** not stated in the table or text.
  - Inference, not stated: specimen depths for the same holes (Tables 4.2-4.4) are in ft and lie within the hole depths. The elevations (1316-1612) would be impossible in metres for Minnesota. Both columns are therefore almost certainly **feet**.
- **Coordinate system:** **not stated**.
  - The report gives no name or definition for "CC" (presumably a county coordinate system).
  - The report states no UTM zone and no datum for either system.
  - Inference, not stated: for all 105 pairs of borings, the distance computed from UTM divided by the distance computed from CC equals 0.3048 ± 1 %. So CC North/East are in **feet** and UTM in **metres**.
  - Inference, not stated: read as UTM zone 15N, the UTM values fall at about 47.51-47.52° N, 92.51-92.52° W (northern St. Louis County, near Virginia/Eveleth, MN). That is consistent with the TH 53 / United Taconite description, but the zone and datum are an inference.
- **Boreholes not listed in Table 4.1:** Tables 4.2-4.4 also contain specimens from DBA-07, DBA-08, DBA-09, IDH-01, IDH-06 and IDH-07. These have no location in Table 4.1.
  - Specimen boreholes are written "DBA-01a-xx" in Table 4.2/4.3 but "DBA-01A" for IDs 121-122 in Table 4.4. Both are kept as printed.

### Source inconsistencies noted (flagged in the `doubt` column of mndot_ucs.csv)
- **#3:** UCS and E are N/A. The specimen failed during tuning.
  - Sec. 3.4.3 (p. 13) says failure was at "approximately 150 kN (axial stress = 74 MPa). No data acquisition was running, so an exact value is not available."
  - The same section calls this specimen "specimen #3 (SB-12 184.9-185.2 ft.)", whereas the table has SD-12.
- **#44 and #97:** N/A values; "Specimen fractured during preparation".
- **#50:** depth interval 364.2-370.0 ft (5.8 ft).
- **#104:** from = to = 292.1 ft.
- **#131:** to (200.1) < from (200.8).
- **#133:** 358.7-386.3 ft (27.6 ft).
  - The depth problems in #50, #104, #131 and #133 are identical in the US-unit tables.
- **#120 (DBA-01):** Table 4.4 and the Appendix A header give UCS 107.4 MPa and E 53.8 GPa. However:
  - Table 4.7 gives 1.3 ksi (about 9 MPa).
  - Fig. A.236 shows a peak of about 53-54 MPa and a fit slope of 1.7984 per 1e-4, i.e. about 18 GPa.
  - This was the only specimen whose Appendix A slope disagrees with its tabulated E (all 130 others with data agree within 6 %).
- Sec. 4.1 garbles the table numbering: "Tables 4.2-4.4 in SI units (Tables 4.4-4.6) and the same results in English units (Tables 4.5-4.7)".

---

## Data set 2: SP2782-334 (Sec. 5.2.1; Tables 5.1 + 5.2; triaxial, 6 specimens x1-x6)

- **Project name:** "SP2782-334". This is the label used in the section heading 5.2.1, in Appendix B ("Stress - Strain Plots SP2782-334", samples x1-x6) and in Appendix E ("Photos of Triaxial Specimens For SP2782-334", specimens x1-x6).
  - The report does not say what the label denotes. It is presumably a MnDOT State Project number, but that is not stated.
- **Location:** **not stated**. No county, city or coordinates are given; the Hole ID is T06.
- **Lithology / formation:** from Table 5.1 "Labeling, depth, and stratigraphy for each sample" (p. 24 / PDF 34):
  - x1-x5: **Platteville** Formation, members Magnolia (x1), Hidden Falls (x2), Mifflin (x3, x4), Pecatonica (x5).
  - x6: **Glenwood Shale**, member N/A.
  - Depths 74.4-101.025 ft in hole T06.
  - The rock type (e.g. limestone/dolostone) is not given beyond the formation names.
- **CONFLICT in the report text:**
  - Sec. 5.1 (p. 23 / PDF 33) says: "Triaxial compression testing was performed on St. Peter Sandstone, where specimens were machined from a block provided by MnDOT. ... Results for the St. Peter Sandstone are in Table 5.1; stress-strain curves are in Appendix C and photos of the specimens and coring process are presented in Appendix F."
  - The same paragraph says "The results from triaxial compression testing for SP2782-334 are reported in Table 5.3 and for SP804-81 in Table 5.4."
  - These sentences contradict the document structure: Tables 5.1/5.2 sit under heading 5.2.1 "SP2782-334 Results", and Table 5.1 lists Platteville/Glenwood, not St. Peter Sandstone.
  - The St. Peter Sandstone specimens are actually **SPSS 1-4**. Their stress-strain plots are in Appendix D (sigma3 = 1, 0, 2.5, 5 MPa) and their photos and coring set-up are in Appendix G (Fig. G.9).
  - **No table of St. Peter results exists in the report.** 6 (x) + 23 (SP804-81) + 4 (SPSS) = 33, which matches the 33 triaxial tests stated.
  - Conclusion: **Tables 5.1/5.2 are the SP2782-334 set (Platteville Fm. / Glenwood Shale), not St. Peter Sandstone.**
- **Friction angle:** not tabulated per specimen. The text (p. 23) says:
  - "From Figure 5.1, an estimate of friction angle for group A is 48.7 degrees with an R-squared of 0.93. Group B cannot yield a realistic friction angle due to the specimens not being of the similar material."
  - "From Figure 5.2, an estimate of friction angle for group B is 35.1 degrees with an R-squared of 0.98."
  - Figure 5.2 actually defines groups C (x1, x2, x6) and D (x3, x4, x5), so the "group B" in that sentence is ambiguous.
  - These values were not written into friction_deg in the CSV. The `group` column records both groupings, e.g. "Fig5.1:A;Fig5.2:C".
- Specimen size: D about 44.4-44.8 mm, L about 92-96 mm. Confinement sigma3 = 5, 10 or 20 MPa.

---

## Data set 3: SP804-81 (Sec. 5.2.2; Tables 5.3 + 5.4; triaxial, 23 specimens 7-29)

- **Project name:** "SP804-81". This label is used in heading 5.2.2, Appendix C ("Stress - Strain Plots SP804-81", specimens 7-29, triaxial groups 1-7) and the Sec. 5.1 text. Its meaning is not stated.
  - Appendix F's title says "SP2782-334", but it shows specimens 7-29. This is a labelling error in the report.
- **Location:** **not stated**. The cores are identified only by Unique# 80240, 80241, 80242 and 80243, which do not appear in Table 4.1.
- **Lithology:** Table 5.3 "Labeling, depth and stratigraphy for each sample" (p. 25-26 / PDF 35-36) gives Stratigraphy = **"Cretaceous Sediments"** for all 23 samples.
  - No rock name is given.
  - Depths are 40.3-87.4 ft. Densities are 1.89-2.19 g/cm3 and Vp 1191-2403 m/s, which indicates weak sedimentary material.
- **Friction angle:** Table 5.4 gives one value per triaxial group (merged cell). The CSV repeats it on every row of the group.
  - Group 1 = 25.5, 2 = 34.4, 3 = 52.1, 4 = 18.9, 5 = 19.2, 6 = 28.6, 7 = N/A.
  - Re-fitting sigma1 = N sigma3 + C0 reproduces groups 1, 2, 4, 5 and 6, as do the Fig. 5.3, 5.4 and 5.6 equations.
  - **Group 3 (52.1°) is inconsistent**: Fig. 5.5 gives y = 3.6676x + 32.928 with R² = 0.161, which implies about 34.9°. This is flagged in the CSV.
- Specimens 17 and 21 have sigma3 = 0.0. Appendix C/F captions read "σ3=0 MPa, leaked", meaning the confining pressure leaked. This is flagged.
- Specimen size: D about 42.5-45.3 mm, L about 59-96 mm (several have L:D well below 2). Confinement sigma3 = 0-10 MPa.
