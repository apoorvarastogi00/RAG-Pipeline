# Evaluation Results

Questions: 35
Top-k: 7
Mode: `retrieval_proxy`
Generator/Judge model in `--full` mode: `llama-3.3-70b-versatile`

## Summary

| Category | Count | Retrieval Hit-Rate | Answer Correctness |
|---|---:|---:|---:|
| easy_lookup | 12 | 83.3% | 83.3% |
| multi_section | 10 | 85.0% | 70.0% |
| cross_document | 7 | 78.6% | 71.4% |
| out_of_scope | 6 | 100.0% | 100.0% |
| **TOTAL** | 35 | 85.7% | 80.0% |

## Per-question Results

| # | Category | Retrieval | Correct | Expected | Retrieved | Question |
|---:|---|---:|---|---|---|---|
| 1 | easy_lookup | 100% | yes | BNS s.103 | BNS s.103, BNSS s.456, BNS s.104, BNS s.109, BNSS s.464, BNS s.4, BNSS s.454 | What is the punishment for murder? |
| 2 | easy_lookup | 100% | yes | BNS s.70 | BNS s.75, BNS s.64, BNS s.70, BNS s.69, BNSS s.289, BNS s.196 | How is gang rape punished? |
| 3 | easy_lookup | 100% | yes | BNS s.303 | BNS s.305, BNS s.304, BNS s.309, BNS s.303, BNSS s.499, BNS s.243 | What is the definition of theft? |
| 4 | easy_lookup | 100% | yes | BNSS s.35 | BNSS s.35, BNSS s.57, BNSS s.58, BNSS s.47, BNS s.208, BNSS s.78 | When can police arrest without a warrant? |
| 5 | easy_lookup | 100% | yes | BNSS s.97 | BNSS s.97, BNSS s.103, BNSS s.96, BNS s.317, BNSS s.201, BNSS s.186, BNSS s.44 | How is a search warrant issued for a place suspected to contain stolen property? |
| 6 | easy_lookup | 100% | yes | BNSS s.39 | BNSS s.39, BNSS s.40, BNSS s.54, BNS s.351, BNS s.213, BNS s.215, BNSS s.44 | What happens if an arrested person refuses to give their name and residence? |
| 7 | easy_lookup | 100% | yes | BNSS s.40 | BNSS s.40, BNSS s.49, BNSS s.39, BNSS s.35, BNSS s.41, BNSS s.43 | Can a private person arrest someone? |
| 8 | easy_lookup | 0% | no | BNSS s.479 | BNS s.127, BNS s.264, BNSS s.187, BNS s.261, BNS s.136, BNS s.12, BNSS s.468 | What is the maximum period an undertrial prisoner can be detained? |
| 9 | easy_lookup | 0% | no | BNSS s.43 | BNS s.4, BNSS s.50, BNSS s.72, BNSS s.457, BNSS s.48, BNS s.252, BNS s.1 | How is an arrest made according to the Sanhita? |
| 10 | easy_lookup | 100% | yes | BNSS s.47 | BNSS s.47, BNSS s.48, BNSS s.36, BNSS s.77, BNSS s.82, BNSS s.54, BNSS s.35 | Must an arrested person be informed of the grounds of their arrest? |
| 11 | easy_lookup | 100% | yes | BNSS s.58 | BNSS s.187, BNSS s.170, BNSS s.58, BNS s.355, BNSS s.40, BNSS s.78 | Can a person be detained for more than 24 hours? |
| 12 | easy_lookup | 100% | yes | BNSS s.478 | BNSS s.478, BNSS s.480, BNSS s.490, BNSS s.481, BNS s.140, BNSS s.488, BNS s.242 | In what cases is bail to be taken? |
| 13 | multi_section | 100% | yes | BNS s.305, BNS s.306 | BNS s.306, BNS s.305, BNSS s.337, BNSS s.129, BNS s.329, BNS s.331, BNS s.303 | If someone commits theft in a dwelling house, and their servant also commits theft of the master's property, what are the relevant sections? |
| 14 | multi_section | 100% | yes | BNS s.103, BNS s.104 | BNS s.103, BNS s.71, BNS s.104, BNS s.105, BNS s.109, BNSS s.475, BNS s.66 | What is the punishment for murder, and what if it is committed by a life-convict? |
| 15 | multi_section | 100% | yes | BNS s.101, BNS s.105 | BNS s.3, BNS s.101, BNS s.110, BNS s.105, BNS s.106, BNSS s.337 | How do you distinguish between murder and culpable homicide not amounting to murder? |
| 16 | multi_section | 100% | yes | BNSS s.53, BNSS s.52 | BNSS s.52, BNSS s.53, BNSS s.51, BNSS s.184, BNSS s.43, BNS s.70, BNSS s.56 | What are the rules regarding the medical examination of an arrested person and a person accused of rape? |
| 17 | multi_section | 50% | no | BNSS s.284, BNSS s.285 | BNSS s.283, BNSS s.383, BNSS s.365, BNSS s.364, BNSS s.284, BNS s.2, BNSS s.286 | Explain the difference between summary trials by a second-class Magistrate and the general procedure for summary trials. |
| 18 | multi_section | 100% | yes | BNSS s.82, BNSS s.83 | BNSS s.75, BNSS s.82, BNSS s.41, BNSS s.132, BNSS s.83, BNSS s.267, BNSS s.54 | What is the procedure when a person is arrested against whom a warrant is issued, and what does the Magistrate do? |
| 19 | multi_section | 100% | yes | BNSS s.497, BNSS s.498 | BNSS s.497, BNSS s.498, BNSS s.503, BNSS s.293, BNSS s.88, BNSS s.504 | How are properties disposed of pending a trial and at the conclusion of a trial? |
| 20 | multi_section | 50% | no | BNSS s.480, BNSS s.483 | BNSS s.480, BNSS s.478, BNSS s.482, BNSS s.47, BNSS s.430, BNS s.269 | Can a person be released on bail for a non-bailable offence, and what are the special powers of the High Court? |
| 21 | multi_section | 50% | no | BNSS s.482, BNSS s.492 | BNSS s.492, BNSS s.478, BNSS s.91, BNSS s.60, BNS s.264, BNSS s.39, BNSS s.83 | How is bail dealt with when the person apprehends arrest, and can a bail bond be cancelled? |
| 22 | multi_section | 100% | yes | BNSS s.355, BNSS s.356 | BNSS s.356, BNSS s.355, BNSS s.335, BNSS s.358, BNSS s.370, BNSS s.371 | What is the procedure when an inquiry or trial is held in the absence of the accused, and what if the person is a proclaimed offender? |
| 23 | cross_document | 100% | yes | BNS s.103, BNSS s.49 | BNS s.104, BNS s.103, BNSS s.49, BNS s.135, BNSS s.53, BNS s.109, BNS s.140 | What is the punishment for murder and how is the search of the arrested person conducted? |
| 24 | cross_document | 100% | yes | BNS s.303, BNSS s.35 | BNS s.304, BNS s.306, BNS s.307, BNS s.134, BNSS s.35, BNSS s.47, BNS s.303 | If someone commits theft, what is the punishment, and can the police arrest them without a warrant? |
| 25 | cross_document | 100% | yes | BNS s.64, BNSS s.184 | BNS s.64, BNS s.70, BNS s.65, BNSS s.184, BNSS s.52, BNSS s.176 | How is rape punished, and what is the medical examination procedure for the victim? |
| 26 | cross_document | 50% | no | BNS s.140, BNSS s.38 | BNS s.140, BNS s.97, BNS s.142, BNSS s.201, BNS s.137, BNS s.139 | What is the penalty for kidnapping to murder, and what are the rights of the arrested person regarding legal representation? |
| 27 | cross_document | 100% | yes | BNS s.269, BNSS s.492 | BNS s.269, BNSS s.492, BNSS s.478, BNSS s.481, BNSS s.430, BNSS s.488 | What is the offence of failing to appear in court after being released on bail, and how is the bond cancelled? |
| 28 | cross_document | 100% | yes | BNS s.109, BNSS s.480 | BNS s.309, BNS s.312, BNS s.226, BNS s.109, BNSS s.480, BNS s.32, BNS s.46 | Is an attempt to murder a bailable offence, and what is the punishment? |
| 29 | cross_document | 0% | no | BNS s.259, BNSS s.206 | BNS s.258, BNS s.257, BNSS s.521, BNS s.161, BNS s.162, BNSS s.520, BNSS s.420 | If an officer commits someone for trial contrary to law, what is their punishment, and how does a High Court decide the place of trial? |
| 30 | out_of_scope | 100% | yes | - | BNS s.285, BNSS s.2, BNSS s.198, BNSS s.197, BNSS s.203, BNSS s.409, BNSS s.206 | What is the capital of France? |
| 31 | out_of_scope | 100% | yes | - | BNSS s.342, BNSS s.423, BNS s.182, BNS s.337, BNSS s.292, BNS s.183, BNS s.184 | How do I file my income tax return? |
| 32 | out_of_scope | 100% | yes | - | BNSS s.379, BNS s.317, BNS s.350, BNS s.304, BNS s.334, BNSS s.499 | What does Section 379 of the IPC say about theft? |
| 33 | out_of_scope | 100% | yes | - | BNSS s.34, BNSS s.320, BNSS s.2, BNS s.297, BNSS s.112, BNS s.9 | Explain the rules of cricket. |
| 34 | out_of_scope | 100% | yes | - | BNS s.234, BNS s.281, BNSS s.447, BNSS s.86, BNSS s.68, BNS s.337, BNSS s.290 | What is the process to apply for a driving license? |
| 35 | out_of_scope | 100% | yes | - | BNS s.114, BNS s.124, BNS s.116, BNSS s.368, BNSS s.367, BNS s.278, BNS s.276 | Can you provide medical advice for a headache? |

## Questions to Inspect

- **easy_lookup** `0%` incorrect: What is the maximum period an undertrial prisoner can be detained? Expected: BNSS s.479. Retrieved: BNS s.127, BNS s.264, BNSS s.187, BNS s.261, BNS s.136, BNS s.12, BNSS s.468. Answer: (not generated in retrieval_proxy mode)
- **easy_lookup** `0%` incorrect: How is an arrest made according to the Sanhita? Expected: BNSS s.43. Retrieved: BNS s.4, BNSS s.50, BNSS s.72, BNSS s.457, BNSS s.48, BNS s.252, BNS s.1. Answer: (not generated in retrieval_proxy mode)
- **multi_section** `50%` incorrect: Explain the difference between summary trials by a second-class Magistrate and the general procedure for summary trials. Expected: BNSS s.284, BNSS s.285. Retrieved: BNSS s.283, BNSS s.383, BNSS s.365, BNSS s.364, BNSS s.284, BNS s.2, BNSS s.286. Answer: (not generated in retrieval_proxy mode)
- **multi_section** `50%` incorrect: Can a person be released on bail for a non-bailable offence, and what are the special powers of the High Court? Expected: BNSS s.480, BNSS s.483. Retrieved: BNSS s.480, BNSS s.478, BNSS s.482, BNSS s.47, BNSS s.430, BNS s.269. Answer: (not generated in retrieval_proxy mode)
- **multi_section** `50%` incorrect: How is bail dealt with when the person apprehends arrest, and can a bail bond be cancelled? Expected: BNSS s.482, BNSS s.492. Retrieved: BNSS s.492, BNSS s.478, BNSS s.91, BNSS s.60, BNS s.264, BNSS s.39, BNSS s.83. Answer: (not generated in retrieval_proxy mode)
- **cross_document** `50%` incorrect: What is the penalty for kidnapping to murder, and what are the rights of the arrested person regarding legal representation? Expected: BNS s.140, BNSS s.38. Retrieved: BNS s.140, BNS s.97, BNS s.142, BNSS s.201, BNS s.137, BNS s.139. Answer: (not generated in retrieval_proxy mode)
- **cross_document** `0%` incorrect: If an officer commits someone for trial contrary to law, what is their punishment, and how does a High Court decide the place of trial? Expected: BNS s.259, BNSS s.206. Retrieved: BNS s.258, BNS s.257, BNSS s.521, BNS s.161, BNS s.162, BNSS s.520, BNSS s.420. Answer: (not generated in retrieval_proxy mode)
