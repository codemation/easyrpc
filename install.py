#!/usr/bin/env python
if __name__=='__main__':
    import os, sys
    #Check for bin path - install in venv/bin/ if active - else /usr/bin/
    env = sys.prefix
    version = f'python{sys.version_info[0]}.{sys.version_info[1]}'
    install_dir = f'{env}/lib/{version}/easyrpc'
    if 'install' in sys.argv:
        try:
            os.makedirs(install_dir)
            os.system(f'cp easyrpc/*.py README.md {install_dir}')
            print("easyrpc successfully installed - see https://github.com/codemation/easyrpc for usage")
        except Exception as e:
            error = repr(e)
            if 'Permission denied' in error:
                print(f'{error} - try sudo ./setup.py install')
            else:
                print(error)
    elif 'remove' in sys.argv:
        try:
            os.system(f'rm -rf {install_dir}')
        except Exception as e:
            error = repr(e)
            if 'Permission denied' in error:
                print(f'{error} - try sudo ./setup.py remove')
            else:
                print(error)
    else:
        print("missing flag - install|remove")