// Ramesh persona — SYNTHETIC, FICTIONAL sample data written for the demo.
// Not a real person; no real rules are encoded here. Shows: Devanagari names
// with transliteration, an unreadable address (confidence null -> "Please
// check this", UNKNOWN status), a POSSIBLE_VARIANT name and a MATCH.

import type { Persona } from "@/mock/types";

export const ramesh: Persona = {
  id: "ramesh",
  label: "Ramesh",
  service_id: "pm_kisan",
  life_events: ["address_change"],
  documents: [
    {
      id: "ramesh_aadhaar",
      document_type: "aadhaar",
      filename: "ramesh_aadhaar.jpg",
      fields: [
        { name: "full_name", raw_value: "रमेश कुमार", normalized_value: "Ramesh Kumar", confidence: 0.94, evidence: "Name field, front of card" },
        { name: "date_of_birth", raw_value: "01/01/1970", normalized_value: "1970-01-01", confidence: 0.9, evidence: "DOB field, front of card" },
        { name: "gender", raw_value: "पुरुष", normalized_value: "male", confidence: 0.97, evidence: "Gender field, front of card" },
        { name: "address", raw_value: "ग्राम बेलवा, जिला गोरखपुर", normalized_value: "Gram Belwa, Jila Gorakhpur", confidence: 0.83, evidence: "Address, back of card" },
      ],
    },
    {
      id: "ramesh_bank",
      document_type: "bank_passbook",
      filename: "ramesh_passbook.jpg",
      fields: [
        { name: "account_holder_name", raw_value: "RAMESH KUMAR YADAV", normalized_value: "Ramesh Kumar Yadav", confidence: 0.88, evidence: "Account holder name, first page" },
        { name: "father_name", raw_value: "SITA RAM YADAV", normalized_value: "Sita Ram Yadav", confidence: 0.66, evidence: "S/o line, first page (smudged)" },
      ],
    },
    {
      id: "ramesh_land",
      document_type: "other",
      filename: "ramesh_land_record.jpg",
      fields: [
        { name: "full_name", raw_value: "रमेश कुमार यादव", normalized_value: "Ramesh Kumar Yadav", confidence: 0.79, evidence: "Owner name on land record" },
        { name: "father_name", raw_value: "सीता राम यादव", normalized_value: "Sita Ram Yadav", confidence: 0.81, evidence: "Father's name on land record" },
        // Could not be read: confidence null -> "Please check this".
        { name: "address", raw_value: "", normalized_value: "", confidence: null, evidence: "Village field, torn corner" },
      ],
    },
  ],
  check: {
    mismatches: [
      {
        field: "full_name",
        document_ids: ["ramesh_aadhaar", "ramesh_bank", "ramesh_land"],
        values: {
          ramesh_aadhaar: "रमेश कुमार / Ramesh Kumar",
          ramesh_bank: "Ramesh Kumar Yadav",
          ramesh_land: "रमेश कुमार यादव / Ramesh Kumar Yadav",
        },
        status: "POSSIBLE_VARIANT",
        explanation:
          "Aadhaar does not include the surname 'Yadav', which the bank and land record do. These are likely the same person, but this is not certain. Do not remove any part of the name.",
      },
      {
        field: "father_name",
        document_ids: ["ramesh_bank", "ramesh_land"],
        values: { ramesh_bank: "Sita Ram Yadav", ramesh_land: "सीता राम यादव / Sita Ram Yadav" },
        status: "MATCH",
        explanation: "Father's name reads the same on the passbook and the land record.",
      },
      {
        field: "address",
        document_ids: ["ramesh_aadhaar", "ramesh_land"],
        values: { ramesh_aadhaar: "Gram Belwa, Jila Gorakhpur", ramesh_land: "" },
        status: "UNKNOWN",
        explanation:
          "We could not read the village on the land record (the corner is torn), so we cannot compare addresses.",
      },
    ],
    readiness: {
      service_id: "pm_kisan",
      status: "UNVERIFIED",
      findings: [
        {
          mismatch_field: "full_name",
          classification: "VERIFY_AT_OFFICE",
          reason:
            "The surname 'Yadav' is missing on Aadhaar. Ask the office whether this is acceptable for linking your bank account and land record.",
          rule_id: null,
        },
        {
          mismatch_field: "address",
          classification: "VERIFY_AT_OFFICE",
          reason: "The land record address could not be read. Carry the original land record.",
          rule_id: null,
        },
      ],
      unresolved_questions: [
        "Is the land record in your name exactly as written on Aadhaar?",
        "Which village is written on the land record?",
      ],
      next_steps: [
        "Take a clearer photo of the land record, or carry the original.",
        "Ask the office whether the missing surname on Aadhaar needs to be updated.",
      ],
    },
    correction_path: [],
    correction_path_dot: "digraph correction_path {\n}\n",
    sources: ["https://uidai.gov.in/", "https://www.rbi.org.in/"],
  },
};
