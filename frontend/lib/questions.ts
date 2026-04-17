export type Question = {
  id: string;
  text: string;
  section: string;
  tags: string[];
};

export const INTERVIEW_QUESTIONS: Question[] = [
  // ─── Consent & Identity ────────────────────────────────────────────
  { id: 'q1',  section: 'Consent & Identity', tags: ['kyc', 'identity'],   text: 'Can you please confirm your full name as it appears on your Aadhaar or PAN card?' },
  { id: 'q2',  section: 'Consent & Identity', tags: ['consent', 'kyc'],    text: 'I am recording this session for KYC and compliance purposes. Do you give your consent to this video recording?' },
  { id: 'q3',  section: 'Consent & Identity', tags: ['bureau', 'consent'], text: 'Do you consent to us pulling your credit bureau report from CIBIL or Experian to assess your loan eligibility?' },
  { id: 'q4',  section: 'Consent & Identity', tags: ['consent'],           text: 'Are you applying for this loan voluntarily, and is the information you are about to provide true and accurate?' },
  { id: 'q5',  section: 'Consent & Identity', tags: ['identity', 'kyc'],   text: 'Please confirm your registered mobile number and the email address we should use for this application.' },

  // ─── Personal Details ──────────────────────────────────────────────
  { id: 'q6',  section: 'Personal Details', tags: ['identity'],            text: 'What is your date of birth?' },
  { id: 'q7',  section: 'Personal Details', tags: ['identity'],            text: 'What is your gender?' },
  { id: 'q8',  section: 'Personal Details', tags: ['address', 'kyc'],     text: 'What is your current residential address — city, state, and PIN code?' },
  { id: 'q9',  section: 'Personal Details', tags: ['address'],             text: 'How long have you been living at this address?' },
  { id: 'q10', section: 'Personal Details', tags: ['demographic'],         text: 'What is your marital status, and how many dependents do you have?' },
  { id: 'q11', section: 'Personal Details', tags: ['demographic'],         text: 'What is your highest educational qualification?' },

  // ─── Employment & Income ───────────────────────────────────────────
  { id: 'q12', section: 'Employment & Income', tags: ['income', 'employment'], text: 'Are you currently salaried, self-employed, or in any other form of employment?' },
  { id: 'q13', section: 'Employment & Income', tags: ['employment'],           text: 'What is the name of your current employer or business?' },
  { id: 'q14', section: 'Employment & Income', tags: ['employment'],           text: 'What is your current job title or designation?' },
  { id: 'q15', section: 'Employment & Income', tags: ['employment'],           text: 'How long have you been with your current employer or running your current business?' },
  { id: 'q16', section: 'Employment & Income', tags: ['employment'],           text: 'What is your total work experience in years?' },
  { id: 'q17', section: 'Employment & Income', tags: ['income'],               text: 'What is your monthly net take-home salary, or your average monthly income if self-employed?' },
  { id: 'q18', section: 'Employment & Income', tags: ['income', 'banking'],    text: 'Is your salary credited to a bank account? Which bank and branch?' },
  { id: 'q19', section: 'Employment & Income', tags: ['income', 'business'],   text: 'For self-employed applicants: What is your annual business turnover and net profit for the last financial year?' },

  // ─── Loan Intent ───────────────────────────────────────────────────
  { id: 'q20', section: 'Loan Intent', tags: ['loan'],          text: 'What type of loan are you applying for today — personal loan, business loan, or something else?' },
  { id: 'q21', section: 'Loan Intent', tags: ['loan'],          text: 'How much loan amount are you looking for?' },
  { id: 'q22', section: 'Loan Intent', tags: ['loan'],          text: 'What is the primary purpose of this loan?' },
  { id: 'q23', section: 'Loan Intent', tags: ['loan', 'emi'],   text: 'What loan tenure are you comfortable with — in months or years?' },
  { id: 'q24', section: 'Loan Intent', tags: ['emi'],           text: 'What monthly EMI amount would you be comfortable repaying?' },
  { id: 'q25', section: 'Loan Intent', tags: ['bureau', 'loan'], text: 'Have you applied for a loan with any other lender in the last three months?' },

  // ─── Existing Liabilities ──────────────────────────────────────────
  { id: 'q26', section: 'Existing Liabilities', tags: ['liabilities', 'emi'],    text: 'Do you currently have any active loans — home loan, car loan, personal loan, or any others?' },
  { id: 'q27', section: 'Existing Liabilities', tags: ['liabilities', 'emi'],    text: 'How many EMIs are you paying every month, and what is the total combined EMI amount?' },
  { id: 'q28', section: 'Existing Liabilities', tags: ['credit', 'liabilities'], text: 'Do you have any outstanding credit card balance or credit card EMIs?' },
  { id: 'q29', section: 'Existing Liabilities', tags: ['bureau', 'npa'],         text: 'Have you ever had a loan that went overdue for more than 90 days, or been marked as NPA by any lender?' },
  { id: 'q30', section: 'Existing Liabilities', tags: ['bureau', 'settlement'],  text: 'Have any of your loans ever been written off or settled for less than the full amount?' },
  { id: 'q31', section: 'Existing Liabilities', tags: ['liabilities'],           text: 'Are you currently a co-applicant or guarantor on anyone else\'s loan?' },

  // ─── Banking & Assets ──────────────────────────────────────────────
  { id: 'q32', section: 'Banking & Assets', tags: ['banking'],         text: 'Which bank account is your primary salary or income account? Please share the bank name.' },
  { id: 'q33', section: 'Banking & Assets', tags: ['assets', 'banking'], text: 'Do you have any savings, fixed deposits, mutual funds, or investments you would like to declare?' },
  { id: 'q34', section: 'Banking & Assets', tags: ['assets'],          text: 'Do you own any property, land, or vehicle in your name?' },
  { id: 'q35', section: 'Banking & Assets', tags: ['banking', 'fraud'], text: 'Have you had any cheque bounces or ECS failures in the last 6 months to your knowledge?' },
  { id: 'q36', section: 'Banking & Assets', tags: ['fraud', 'legal'],  text: 'Is there any legal case, court order, or financial judgment against you currently?' },

  // ─── Declarations & Consent ────────────────────────────────────────
  { id: 'q37', section: 'Declarations & Consent', tags: ['consent'],       text: 'Do you confirm that all the information you have provided in this call is accurate, complete, and not misleading?' },
  { id: 'q38', section: 'Declarations & Consent', tags: ['consent'],       text: 'Do you consent to receiving your loan offer, communications, and updates via WhatsApp, SMS, and email?' },
  { id: 'q39', section: 'Declarations & Consent', tags: ['policy', 'kyc'], text: 'Are you aware that this loan application is subject to credit checks, policy evaluation, and verification of the documents you will submit?' },
  { id: 'q40', section: 'Declarations & Consent', tags: ['consent'],       text: 'Do you have any questions about the loan process before we proceed to evaluate your application?' },
];
