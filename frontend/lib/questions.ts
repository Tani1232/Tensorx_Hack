export type Question = {
  id: string;
  text: string;
  section: string;
  tags: string[];
};

export const INTERVIEW_QUESTIONS: Question[] = [
  { id: 'q1',  section: 'Identity', tags: ['kyc'], text: 'Confirm your full name?' },
  { id: 'q2',  section: 'Consent',  tags: ['kyc'], text: 'Consent to video recording? (Yes/No)' },
  { id: 'q3',  section: 'Consent',  tags: ['kyc'], text: 'Consent to bureau pull? (Yes/No)' },
  { id: 'q4',  section: 'Profile',  tags: ['age'], text: 'What is your current age?' },
  { id: 'q5',  section: 'Income',   tags: ['job'], text: 'Employment type? (Salaried/Business)' },
  { id: 'q6',  section: 'Income',   tags: ['inc'], text: 'Monthly take-home income?' },
  { id: 'q7',  section: 'Income',   tags: ['ten'], text: 'Months at current job?' },
  { id: 'q8',  section: 'Loan',     tags: ['amt'], text: 'Requested loan amount?' },
  { id: 'q9',  section: 'Loan',     tags: ['dur'], text: 'Loan tenure in months?' },
  { id: 'q10', section: 'Credit',   tags: ['scr'], text: 'Approximate CIBIL score?' },
  { id: 'q11', section: 'Credit',   tags: ['his'], text: 'Credit history in years?' },
  { id: 'q12', section: 'Credit',   tags: ['utl'], text: 'Credit card usage %?' },
  { id: 'q13', section: 'Credit',   tags: ['dpd'], text: 'Any late payments? (Yes/No)' },
  { id: 'q14', section: 'Liability',tags: ['emi'], text: 'Number of active EMIs?' },
  { id: 'q15', section: 'Liability',tags: ['amt'], text: 'Total monthly EMI amount?' },
];
