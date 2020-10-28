"""
Purpose:
Increments current Pypi version by .001
"""
if __name__=='__main__':
    import sys
    version = sys.stdin.readline().rstrip()
    if '(' in version and ')' in version:
        version = version[2:7]
        print(f"{float(version)+0.001:.3f}")