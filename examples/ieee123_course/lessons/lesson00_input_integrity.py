"""Lesson 00: input provenance, immutable cases, and safe output policy.

No simulator, Gurobi, network connection, or external data needed. Learn the
separation between (a) input data, (b) source code, and (c) generated output.
"""
from course_utils.core import verify_inputs,save_json,FEEDERS,master,sha

def run(out,steps):
    report=verify_inputs()
    report['feeders']={name:{'master':str(master(name)),
        'master_sha256':sha(master(name))} for name in FEEDERS}
    report['lesson']='00_input_integrity';report['physics_changed']=False
    save_json(out/'result.json',report)
    print(f"Lesson 00: verified {report['verified_input_files']} input files")
    return report
