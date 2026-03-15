import re
from typing import Dict, Any


def extract_legal_metadata(text: str, filename: str) -> Dict:
	"""
	Best-effort extraction of core legal metadata from a judgment.
	This is intentionally simple for Phase 1 and can be improved later.
	"""
	meta: Dict = {}
	meta["doc_id"] = filename
	meta["filename"] = filename

	header = text[:4000] if text else ""
	header_up = header.upper()

	# Court (e.g. "IN THE COURT OF APPEAL", "IN THE HIGH COURT OF KENYA")
	court_match = re.search(r"IN THE\s+(.+?COURT.+?)(?:\n|$)", header_up)
	if court_match:
		meta["court"] = court_match.group(1).title().strip()

	# Station / location (e.g. "AT NAKURU", "AT NAIROBI")
	station_match = re.search(r"\bAT\s+([A-Z][A-Z\s]+)", header_up)
	if station_match:
		meta["station"] = station_match.group(1).title().strip()

	# Case citation / number (try broad pattern: "... NO. ... OF 2012")
	case_cit_match = re.search(
		r"((?:CIVIL|CRIMINAL|APPLICATION|PETITION|ADVISORY OPINION|C\.A\.|H\.C\.CR\.A\.)"
		r"[\w\s\.\-&/]*?NO\.?\s*[\w\s\.\-&/]+?\s+OF\s+\d{4})",
		header_up,
	)
	if case_cit_match:
		full_citation = case_cit_match.group(1).strip()
		meta["full_case_citation"] = full_citation
		# Extract year from citation
		year_match = re.search(r"(\d{4})\s*$", full_citation)
		if year_match:
			try:
				meta["year"] = int(year_match.group(1))
			except ValueError:
				pass

		# Very rough case_number: part after "NO."
		num_match = re.search(r"NO\.?\s*([\w\s\.\-&/]+?)\s+OF\s+\d{4}", full_citation)
		if num_match:
			meta["case_number"] = num_match.group(1).strip()

	# Parties between "BETWEEN" and "AND"
	parties_block = None
	between_match = re.search(r"\bBETWEEN\b([\s\S]+?)\bAND\b", header, re.IGNORECASE)
	if between_match:
		parties_block = between_match.group(1).strip()

	parties = []
	if parties_block:
		for line in parties_block.splitlines():
			line = line.strip()
			if not line:
				continue
			# Strip trailing role markers like "APPELLANT", "RESPONDENT"
			line_clean = re.sub(
				r"\b(APPELLANT|APPLICANT|PETITIONER|RESPONDENT|DEFENDANT|PLAINTIFF)\b\.?",
				"",
				line,
				flags=re.IGNORECASE,
			).strip(" .\t")
			if line_clean:
				parties.append(line_clean)

	if parties:
		meta["parties"] = parties

	# Coram: look for "CORAM:" line
	coram_match = re.search(r"CORAM:\s*([^\n]+)", header, re.IGNORECASE)
	if coram_match:
		coram_raw = coram_match.group(1).strip()
		# Split by commas or "&"
		coram_parts = re.split(r",|&|;", coram_raw)
		coram_clean = [c.strip(" .") for c in coram_parts if c.strip()]
		if coram_clean:
			meta["coram"] = coram_clean

	# Originating case (very rough, e.g. "H.C.CR.A. NO.527 OF 2003")
	orig_match = re.search(r"(H\.?C\.?\.?CR\.?A\.?\s+NO\.?\s*[\w\s\.\-&/]+)", header_up)
	if orig_match:
		meta["originating_case"] = orig_match.group(1).strip()

	return meta


def extract_opening_paragraphs(text: str, max_paragraphs: int = 3) -> str:
	if not text:
		return ""
	paras = [p.strip() for p in text.split("\n\n") if p.strip()]
	return "\n\n".join(paras[:max_paragraphs])


def build_master_text(metadata: Dict, text: str) -> str:
	opening = extract_opening_paragraphs(text, max_paragraphs=3)

	parts = [
		metadata.get("full_case_citation", ""),
		f'Court: {metadata.get("court", "")} {metadata.get("station", "")}'.strip(),
		f'Case number: {metadata.get("case_number", "")}, Year: {metadata.get("year", "")}',
		f'Parties: {", ".join(metadata.get("parties", []))}' if metadata.get("parties") else "",
		f'Coram: {", ".join(metadata.get("coram", []))}' if metadata.get("coram") else "",
		f'Originating case: {metadata.get("originating_case", "")}',
		"Opening paragraphs:",
		opening,
	]
	return "\n".join([p for p in parts if p])


def classify_source(metadata: Dict, filename: str, text: str) -> Dict[str, Any]:
	"""
	Classify a document into high-level data sources:
	- case_law (with court_type)
	- legislation (acts_in_force / repealed_statute)
	- kenya_gazette (with gazette_year)
	"""
	name = (filename or "").lower()
	header = (text or "")[:4000]
	header_up = header.upper()

	out: Dict[str, Any] = {}

	# --- Kenya Gazette ---
	if "gazette" in name or re.search(r"\bKG\b", filename.upper()):
		out["source_type"] = "kenya_gazette"
		year = metadata.get("year")
		if not year:
			m = re.search(r"(\d{4})\s*KG", filename.upper())
			if m:
				try:
					year = int(m.group(1))
				except ValueError:
					year = None
		if year:
			out["gazette_year"] = year
		return out

	# --- Legislation ---
	if (
		"act" in name
		or "statute" in name
		or "legislation" in name
		or "an act of parliament" in header_up
	):
		out["source_type"] = "legislation"
		leg_type = "acts_in_force"
		if "repealed" in name or "repealed" in header_up:
			leg_type = "repealed_statute"
		out["legislation_type"] = leg_type
		return out

	# --- Default: Case law ---
	out["source_type"] = "case_law"
	court_raw = str(metadata.get("court", "") or "").upper()
	court_type = None
	if "SUPREME COURT" in court_raw:
		court_type = "Supreme Court"
	elif "COURT OF APPEAL" in court_raw:
		court_type = "Court of Appeal"
	elif "EMPLOYMENT AND LABOUR RELATIONS" in court_raw or "ELRC" in court_raw:
		court_type = "Employment and Labour Relations Court"
	elif "ENVIRONMENT AND LAND" in court_raw or "ELC" in court_raw:
		court_type = "Environment and Land Court"
	elif "KADHI" in court_raw:
		court_type = "Kadhis Court"
	elif "MAGISTRATE" in court_raw:
		court_type = "Magistrates Courts"
	elif "TRIBUNAL" in court_raw:
		court_type = "Special Tribunals"
	elif "HIGH COURT" in court_raw:
		court_type = "High Court"

	if court_type:
		out["court_type"] = court_type

	return out

