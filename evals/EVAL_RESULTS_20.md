# Evaluation Results

Questions: 20
Dataset: `evals/eval_questions_20.json`
Top-k: 7
Mode: `retrieval_proxy`
Generator/Judge model in `--full` mode: `llama-3.3-70b-versatile`

## Summary

| Category | Count | Retrieval Hit-Rate | Answer Correctness |
|---|---:|---:|---:|
| easy_lookup | 6 | 100.0% | 100.0% |
| multi_section | 5 | 90.0% | 80.0% |
| cross_document | 5 | 100.0% | 100.0% |
| ambiguous_followup | 1 | 100.0% | 100.0% |
| out_of_scope | 3 | 100.0% | 100.0% |
| **TOTAL** | 20 | 97.5% | 95.0% |

## Per-question Results

| # | Category | Retrieval | Correct | Expected | Retrieved | Question |
|---:|---|---:|---|---|---|---|
| 1 | easy_lookup | 100% | yes | BNS s.103 | BNS s.103, BNSS s.456, BNS s.104, BNS s.109, BNSS s.464, BNS s.4, BNSS s.454 | What is the punishment for murder? |
| 2 | easy_lookup | 100% | yes | BNS s.303 | BNS s.305, BNS s.304, BNS s.309, BNS s.303, BNSS s.499, BNS s.243 | What is the definition of theft? |
| 3 | easy_lookup | 100% | yes | BNSS s.35 | BNSS s.35, BNSS s.57, BNSS s.58, BNSS s.47, BNS s.208, BNSS s.78 | When can police arrest without a warrant? |
| 4 | easy_lookup | 100% | yes | BNSS s.47 | BNSS s.47, BNSS s.48, BNSS s.36, BNSS s.77, BNSS s.82, BNSS s.54, BNSS s.35 | Must an arrested person be informed of the grounds of arrest? |
| 5 | easy_lookup | 100% | yes | BNS s.70 | BNS s.64, BNS s.69, BNS s.70, BNS s.135, BNS s.65, BNS s.134 | What is gang rape and how is it punished? |
| 6 | easy_lookup | 100% | yes | BNSS s.478 | BNSS s.478, BNSS s.480, BNSS s.490, BNSS s.481, BNS s.140, BNSS s.488, BNS s.242 | In what cases is bail to be taken? |
| 7 | multi_section | 100% | yes | BNS s.103, BNS s.104 | BNS s.103, BNS s.71, BNS s.104, BNS s.105, BNS s.109, BNSS s.475, BNS s.66 | What is the punishment for murder, and what if it is committed by a life-convict? |
| 8 | multi_section | 100% | yes | BNS s.101, BNS s.105 | BNS s.3, BNS s.101, BNS s.110, BNS s.105, BNS s.106, BNSS s.337 | How do you distinguish between murder and culpable homicide not amounting to murder? |
| 9 | multi_section | 100% | yes | BNSS s.53, BNSS s.52 | BNSS s.52, BNSS s.53, BNSS s.51, BNSS s.184, BNSS s.43, BNS s.65, BNS s.70 | What are the rules for medical examination of an arrested person and of a person accused of rape? |
| 10 | multi_section | 100% | yes | BNSS s.497, BNSS s.498 | BNSS s.497, BNSS s.498, BNSS s.88, BNSS s.293, BNSS s.503, BNSS s.504 | How are properties disposed of pending trial and at the conclusion of trial? |
| 11 | multi_section | 50% | no | BNSS s.480, BNSS s.483 | BNSS s.480, BNSS s.478, BNSS s.482, BNSS s.47, BNSS s.430, BNS s.269 | Can a person be released on bail for a non-bailable offence, and what are the special powers of the High Court? |
| 12 | cross_document | 100% | yes | BNS s.103, BNSS s.248 | BNS s.103, BNS s.104, BNS s.109, BNSS s.248, BNS s.105, BNS s.101, BNS s.110 | What is the punishment for murder and how is the trial conducted? |
| 13 | cross_document | 100% | yes | BNS s.303, BNSS s.35 | BNS s.304, BNS s.306, BNS s.307, BNSS s.35, BNS s.134, BNS s.303, BNSS s.47 | If someone commits theft, what is the punishment, and can police arrest them without a warrant? |
| 14 | cross_document | 100% | yes | BNS s.64, BNSS s.184 | BNS s.64, BNS s.70, BNS s.65, BNSS s.184, BNSS s.52, BNSS s.176 | How is rape punished, and what is the medical examination procedure for the victim? |
| 15 | cross_document | 100% | yes | BNS s.269, BNSS s.492 | BNS s.269, BNSS s.492, BNSS s.478, BNSS s.39, BNSS s.488, BNSS s.481 | What offence is committed by failing to appear after release on bail, and how can the bail bond be cancelled? |
| 16 | ambiguous_followup | 100% | yes | BNS s.109, BNS s.103 | BNS s.132, BNS s.355, BNS s.198, BNS s.201, BNS s.103, BNS s.109, BNS s.101 | If someone shoots a person in public, what will be his punishment? |
| 17 | cross_document | 100% | yes | BNS s.317, BNSS s.97 | BNSS s.201, BNSS s.499, BNSS s.97, BNSS s.244, BNS s.317, BNSS s.107 | If a person is found with stolen property, what offence or procedure may apply? |
| 18 | out_of_scope | 100% | yes | - | BNS s.285, BNSS s.2, BNSS s.198, BNSS s.197, BNSS s.203, BNSS s.409, BNSS s.206 | What is the capital of France? |
| 19 | out_of_scope | 100% | yes | - | BNSS s.342, BNSS s.423, BNS s.182, BNS s.337, BNSS s.292, BNS s.183, BNS s.184 | How do I file my income tax return? |
| 20 | out_of_scope | 100% | yes | - | BNSS s.379, BNS s.317, BNS s.350, BNS s.304, BNS s.334, BNSS s.499 | What does Section 379 of the IPC say about theft? |

## Questions to Inspect

- **multi_section** `50%` incorrect: Can a person be released on bail for a non-bailable offence, and what are the special powers of the High Court? Expected: BNSS s.480, BNSS s.483. Retrieved: BNSS s.480, BNSS s.478, BNSS s.482, BNSS s.47, BNSS s.430, BNS s.269. Answer: (not generated in retrieval_proxy mode)
