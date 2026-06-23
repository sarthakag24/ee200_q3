import fitz
import sys

sys.stdout.reconfigure(encoding='utf-8')

doc = fitz.open(r'c:\ee200_q3\EE200_course_project_summer_2026.pdf')
print(f'Pages: {len(doc)}')
for i in range(len(doc)):
    print(f'--- Page {i+1} ---')
    print(doc[i].get_text())
