@ECHO OFF

pushd %~dp0

REM Command file for Sphinx documentation (Windows)

if "%SPHINXBUILD%" == "" (
	set SPHINXBUILD=sphinx-build
)
set SOURCEDIR=.
set BUILDDIR=_build

%SPHINXBUILD% >NUL 2>NUL
if errorlevel 9009 (
	echo.
	echo.The 'sphinx-build' command was not found. Make sure you installed Sphinx,
	echo.then set the SPHINXBUILD environment variable to the full path of
	echo.the 'sphinx-build' executable. Alternatively, you may add the Sphinx
	echo.directory to PATH.
	echo.
	echo.If you don't have Sphinx installed, install it with:
	echo.   pip install sphinx
	exit /b 1
)

if "%1" == "" goto help

if "%1" == "html" (
	%SPHINXBUILD% -M html %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%
	echo.
	echo.Build finished. The HTML pages are in %BUILDDIR%/html.
	goto end
)

if "%1" == "linkcheck" (
	%SPHINXBUILD% -b linkcheck %SOURCEDIR% %BUILDDIR%/linkcheck %O%
	echo.
	echo.Link check complete; look for any errors in the above output
	echo.or in %BUILDDIR%/linkcheck/output.txt.
	goto end
)

if "%1" == "clean" (
	for /d %%i in (%BUILDDIR%\*) do rmdir /q /s %%i
	del /q /s %BUILDDIR%\*
	goto end
)

:help
%SPHINXBUILD% -M help %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%

:end
popd
