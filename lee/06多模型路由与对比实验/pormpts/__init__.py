# —— 把子模块挂到包上：等价于 PEP 328 子模块回退，但让静态分析（pyright/pylance）
#    也能看到 generate_case_prompt / case_review_prompt / verify_coverage_prompt 这三个名字
from . import generate_case_prompt
from . import case_review_prompt
from . import verify_coverage_prompt
