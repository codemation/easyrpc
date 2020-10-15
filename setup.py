import setuptools
with open("README.md", "r") as fh:
    long_description = fh.read()
setuptools.setup(
     name='easyrpc',  
     version='PYQLVERSION',
     packages=setuptools.find_packages(include=['easyrpc'], exclude=['build']),
     author="Joshua Jamison",
     author_email="joshjamison1@gmail.com",
     description="An easy to use rpc framework for enabling fast inter-process, inter-host communication",
     long_description=long_description,
   long_description_content_type="text/markdown",
     url="https://github.com/codemation/easyrpc",
     classifiers=[
         "Programming Language :: Python :: 3",
         "License :: OSI Approved :: MIT License",
         "Operating System :: OS Independent",
     ],
     python_requires='>=3.7, <4',   
     install_requires=['makefun', 'jwt', 'fastapi', 'uvicorn', 'websockets', 'aiohttp'],
 )