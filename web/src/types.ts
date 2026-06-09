export interface MatchCandidate {
  ka: string;
  title: string;
  description: string;
  score: number;
  classification: string;
}

export interface ExtractedFields {
  description: string;
  address?: string;
  apartment?: string;
  locationDetails?: string;
}

export interface MatchResponse {
  candidates: MatchCandidate[];
  picked_ka: string;
  reasoning: string;
  extracted_fields: ExtractedFields;
}

export interface SubmitPayload {
  ka: string;
  description: string;
  address: string;
  borough: string;
  apartment?: string;
  locationDetails?: string;
  photo_b64?: string;
  language?: string; // if non-English, backend translates description to English for the NYC payload
}

export interface SubmitResponse {
  sr_number: string;
  payload: SubmitPayload;
  status: string;
}

export type AppStep = 'mic' | 'processing' | 'results' | 'form' | 'confirm';

export interface Borough {
  code: string;
  name: string;
}

export const BOROUGHS: Borough[] = [
  { code: 'MANHATTAN', name: 'Manhattan' },
  { code: 'BROOKLYN', name: 'Brooklyn' },
  { code: 'QUEENS', name: 'Queens' },
  { code: 'BRONX', name: 'The Bronx' },
  { code: 'STATEN_ISLAND', name: 'Staten Island' },
];
