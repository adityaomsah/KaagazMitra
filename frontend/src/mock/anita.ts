// Anita persona — SYNTHETIC, FICTIONAL sample data written for the demo.
// Not a real person; no real rules are encoded here (guidance is hedged and
// points to the office). Shows: surname change after marriage (DIFFERENCE),
// a low-confidence date of birth ("Please check this"), spouse_name, address,
// and a MATCH on father's name.

import type { Persona } from "@/mock/types";

export const anita: Persona = {
  id: "anita",
  label: "Anita",
  service_id: "passport_reissue",
  life_events: ["name_change", "address_change"],
  documents: [
    {
      id: "anita_aadhaar",
      document_type: "aadhaar",
      filename: "anita_aadhaar.jpg",
      fields: [
        { name: "full_name", raw_value: "Anita Sharma", normalized_value: "Anita Sharma", confidence: 0.95, evidence: "Name field, front of card" },
        { name: "date_of_birth", raw_value: "15/08/1992", normalized_value: "1992-08-15", confidence: 0.93, evidence: "DOB field, front of card" },
        { name: "gender", raw_value: "Female", normalized_value: "female", confidence: 0.98, evidence: "Gender field, front of card" },
        { name: "address", raw_value: "Flat 12, Shanti Nagar, Pune 411001", normalized_value: "Flat 12, Shanti Nagar, Pune 411001", confidence: 0.81, evidence: "Address, back of card" },
      ],
    },
    {
      id: "anita_pan",
      document_type: "pan",
      filename: "anita_pan.jpg",
      fields: [
        { name: "full_name", raw_value: "ANITA VERMA", normalized_value: "Anita Verma", confidence: 0.9, evidence: "Name field" },
        { name: "father_name", raw_value: "SURESH VERMA", normalized_value: "Suresh Verma", confidence: 0.88, evidence: "Father's name field" },
        { name: "date_of_birth", raw_value: "15/08/1992", normalized_value: "1992-08-15", confidence: 0.86, evidence: "DOB field" },
      ],
    },
    {
      id: "anita_marksheet",
      document_type: "class10_marksheet",
      filename: "anita_class10.jpg",
      fields: [
        { name: "full_name", raw_value: "Anita Verma", normalized_value: "Anita Verma", confidence: 0.91, evidence: "Candidate name on marksheet" },
        // Faded print -> low confidence, triggers "Please check this".
        { name: "date_of_birth", raw_value: "15/08/1993", normalized_value: "1993-08-15", confidence: 0.58, evidence: "DOB on marksheet header (faded)" },
        { name: "father_name", raw_value: "Suresh Verma", normalized_value: "Suresh Verma", confidence: 0.89, evidence: "Father's name on marksheet" },
      ],
    },
    {
      id: "anita_marriage",
      document_type: "marriage_certificate",
      filename: "anita_marriage.jpg",
      fields: [
        { name: "full_name", raw_value: "Anita Verma", normalized_value: "Anita Verma", confidence: 0.92, evidence: "Bride name on certificate" },
        { name: "spouse_name", raw_value: "Rajesh Sharma", normalized_value: "Rajesh Sharma", confidence: 0.9, evidence: "Groom name on certificate" },
      ],
    },
  ],
  check: {
    mismatches: [
      {
        field: "full_name",
        document_ids: ["anita_aadhaar", "anita_pan", "anita_marksheet", "anita_marriage"],
        values: {
          anita_aadhaar: "Anita Sharma",
          anita_pan: "Anita Verma",
          anita_marksheet: "Anita Verma",
          anita_marriage: "Anita Verma",
        },
        status: "DIFFERENCE",
        explanation:
          "The surname is Sharma on Aadhaar but Verma on the other documents. This often happens after marriage. The marriage certificate shows the link, but the office decides which name to use.",
      },
      {
        field: "date_of_birth",
        document_ids: ["anita_aadhaar", "anita_pan", "anita_marksheet"],
        values: {
          anita_aadhaar: "1992-08-15",
          anita_pan: "1992-08-15",
          anita_marksheet: "1993-08-15",
        },
        status: "DIFFERENCE",
        explanation:
          "The year of birth on the marksheet (1993) differs from Aadhaar and PAN (1992). The marksheet print was faded, so this may be a reading mistake. Please compare with the original.",
      },
      {
        field: "father_name",
        document_ids: ["anita_pan", "anita_marksheet"],
        values: { anita_pan: "Suresh Verma", anita_marksheet: "Suresh Verma" },
        status: "MATCH",
        explanation: "Father's name is the same on PAN and the marksheet.",
      },
    ],
    readiness: {
      service_id: "passport_reissue",
      status: "NEEDS_DOCUMENTS",
      findings: [
        {
          mismatch_field: "full_name",
          classification: "NEEDS_SUPPORTING_DOC",
          reason:
            "Your name changed after marriage. Keep your marriage certificate ready to show that 'Anita Verma' and 'Anita Sharma' are the same person.",
          rule_id: null,
        },
        {
          mismatch_field: "date_of_birth",
          classification: "VERIFY_AT_OFFICE",
          reason:
            "The marksheet year may have been misread. Check the original; if it really says 1993, ask the office which date they will accept.",
          rule_id: null,
        },
      ],
      unresolved_questions: [
        "Which name do you want on the new passport: 'Anita Sharma' or 'Anita Verma'?",
        "Does the original marksheet show 1992 or 1993?",
      ],
      next_steps: [
        "Check the date of birth on your original Class 10 marksheet.",
        "Keep the original marriage certificate with your application.",
        "Ask the passport office which proof they accept for a name change after marriage.",
      ],
    },
    correction_path: [],
    correction_path_dot: "digraph correction_path {\n}\n",
    sources: ["https://uidai.gov.in/", "https://www.incometax.gov.in/"],
  },
};
