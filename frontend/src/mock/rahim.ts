// Rahim persona — copied from backend/mock/documents.json and
// backend/mock/check_response.json. FICTIONAL sample data, not a real person.
// Shows POSSIBLE_VARIANT (name spellings) and MATCH (date of birth).

import type { CheckResponse, Document } from "@/types/api";
import type { Persona } from "@/mock/types";

const documents: Document[] = [
  {
    id: "doc_aadhaar",
    document_type: "aadhaar",
    filename: "rahim_aadhaar.jpg",
    fields: [
      { name: "full_name", raw_value: "रहीम खान", normalized_value: "Rahim Khan", confidence: 0.96, evidence: "Name field, front of card" },
      { name: "date_of_birth", raw_value: "12/04/1985", normalized_value: "1985-04-12", confidence: 0.91, evidence: "DOB field, front of card" },
      { name: "gender", raw_value: "Male", normalized_value: "male", confidence: 0.99, evidence: "Gender field, front of card" },
      { name: "aadhaar_number", raw_value: "XXXX XXXX 4821", normalized_value: "XXXX XXXX 4821", confidence: 0.93, evidence: "Aadhaar number, masked for safety" },
    ],
  },
  {
    id: "doc_pan",
    document_type: "pan",
    filename: "rahim_pan.jpg",
    fields: [
      { name: "full_name", raw_value: "RAHMAN KHAN", normalized_value: "Rahman Khan", confidence: 0.88, evidence: "Name field" },
      { name: "father_name", raw_value: "ABDUL KHAN", normalized_value: "Abdul Khan", confidence: 0.85, evidence: "Father's name field" },
      { name: "pan_number", raw_value: "ABCDE1234F", normalized_value: "ABCDE1234F", confidence: 0.95, evidence: "PAN number" },
    ],
  },
  {
    id: "doc_bank",
    document_type: "bank_passbook",
    filename: "rahim_bank_passbook.jpg",
    fields: [
      { name: "account_holder_name", raw_value: "MD RAHIM KHAN", normalized_value: "Md Rahim Khan", confidence: 0.9, evidence: "Account holder name, first page" },
      { name: "account_number", raw_value: "XXXXXX3947", normalized_value: "XXXXXX3947", confidence: 0.97, evidence: "Account number, first page" },
      { name: "ifsc", raw_value: "SBIN0001234", normalized_value: "SBIN0001234", confidence: 0.98, evidence: "IFSC code" },
    ],
  },
  {
    id: "doc_marksheet",
    document_type: "class10_marksheet",
    filename: "rahim_class10.jpg",
    fields: [
      { name: "full_name", raw_value: "Rahim Uddin Khan", normalized_value: "Rahim Uddin Khan", confidence: 0.89, evidence: "Candidate name on marksheet" },
      { name: "date_of_birth", raw_value: "12-04-1985", normalized_value: "1985-04-12", confidence: 0.87, evidence: "DOB on marksheet header" },
      { name: "mother_name", raw_value: "Fatima Bibi", normalized_value: "Fatima Bibi", confidence: 0.84, evidence: "Mother's name on marksheet" },
    ],
  },
  {
    id: "doc_marriage",
    document_type: "marriage_certificate",
    filename: "rahim_marriage.jpg",
    fields: [
      { name: "full_name", raw_value: "Rahim Khan", normalized_value: "Rahim Khan", confidence: 0.92, evidence: "Groom name on certificate" },
      { name: "spouse_name", raw_value: "Ayesha Begum", normalized_value: "Ayesha Begum", confidence: 0.9, evidence: "Bride name on certificate" },
      { name: "date_of_marriage", raw_value: "18/02/2010", normalized_value: "2010-02-18", confidence: 0.88, evidence: "Date of marriage" },
    ],
  },
];


const check: CheckResponse = {
  mismatches: [
    {
      field: "full_name",
      document_ids: ["doc_aadhaar", "doc_pan", "doc_bank", "doc_marksheet", "doc_marriage"],
      values: {
        doc_aadhaar: "रहीम खान / Rahim Khan",
        doc_pan: "Rahman Khan",
        doc_bank: "Md Rahim Khan",
        doc_marksheet: "Rahim Uddin Khan",
        doc_marriage: "Rahim Khan",
      },
      status: "POSSIBLE_VARIANT",
      explanation:
        "The name is spelled and abbreviated differently across documents (Rahman vs Rahim, Md prefix, Uddin middle name). RapidFuzz scores are high enough to treat these as likely variants of the same person rather than a different identity, but this is not certain. Do not remove any name component.",
    },
    {
      field: "date_of_birth",
      document_ids: ["doc_aadhaar", "doc_marksheet"],
      values: { doc_aadhaar: "1985-04-12", doc_marksheet: "1985-04-12" },
      status: "MATCH",
      explanation: "Date of birth is identical across Aadhaar and the Class 10 marksheet.",
    },
  ],
  readiness: {
    service_id: "old_age_pension",
    status: "NEEDS_DOCUMENTS",
    findings: [
      {
        mismatch_field: "full_name",
        classification: "NEEDS_SUPPORTING_DOC",
        reason:
          "For the pension, the name on the Aadhaar must match the bank account. The bank passbook reads 'Md Rahim Khan' while Aadhaar reads 'Rahim Khan'. A supporting document (e.g. a bank confirmation or a name-change/gazette copy) can link the two spellings.",
        rule_id: "rule_pension_name_match",
      },
      {
        mismatch_field: "full_name",
        classification: "VERIFY_AT_OFFICE",
        reason:
          "The PAN spelling 'Rahman Khan' differs from Aadhaar. PAN is not strictly required for this pension, but the office may ask about the difference. Verify in person.",
        rule_id: null,
      },
    ],
    unresolved_questions: [
      "Is the legal name 'Rahim Khan' or 'Rahman Khan'?",
      "Does the bank allow the account name to be updated to match Aadhaar, or is a linking affidavit acceptable?",
    ],
    next_steps: [
      "Collect a bank confirmation letter that links 'Md Rahim Khan' to 'Rahim Khan'.",
      "Carry all original documents to the pension office for name verification.",
      "Do not remove 'Uddin' or 'Md' from any document yourself.",
    ],
  },
  correction_path: [
    {
      order: 1,
      rule_id: "corr_name_gazette",
      action:
        "If 'Rahim Khan' is the correct legal name, publish a name-change gazette notification to unify the spelling across PAN and bank records.",
      depends_on: [],
      is_deadlock: false,
    },
    {
      order: 2,
      rule_id: "corr_bank_name_update",
      action:
        "Visit the bank with Aadhaar and the gazette copy to update the account holder name to match Aadhaar exactly.",
      depends_on: ["corr_name_gazette"],
      is_deadlock: false,
    },
    {
      order: 3,
      rule_id: "corr_pan_name_update",
      action:
        "Apply to update the PAN name from 'Rahman Khan' to the Aadhaar spelling using the same gazette notification.",
      depends_on: ["corr_name_gazette"],
      is_deadlock: false,
    },
  ],
  correction_path_dot:
    'digraph correction_path {\n  rankdir=LR;\n  node [shape=box, style=rounded];\n  "1. Name-change gazette";\n  "2. Update bank account name";\n  "3. Update PAN name";\n  "1. Name-change gazette" -> "2. Update bank account name";\n  "1. Name-change gazette" -> "3. Update PAN name";\n}\n',
  sources: ["https://egazette.gov.in/", "https://www.incometax.gov.in/", "https://uidai.gov.in/"],
};

export const rahim: Persona = {
  id: "rahim",
  label: "Rahim",
  service_id: "old_age_pension",
  life_events: [],
  documents,
  check,
};
