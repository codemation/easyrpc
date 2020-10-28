"""
Purpose:
Increments current Pypi version by .001

Usage: 
    pip3 download easyrpc && ls easyrpc*.whl | sed 's/-/" "/g' | awk '{print "(" $2 ")"}' |  python3 python/easyrpc/easyrpc/nextbuild.py
"""
if __name__=='__main__':
    import sys
    version = sys.stdin.readline().rstrip()
    if '(' in version and ')' in version:
        right_i = version.index('(')
        left_i = version.index(')')
        version = version[right_i+1:left_i]
        print(f"{float(version)+0.001:.3f}")