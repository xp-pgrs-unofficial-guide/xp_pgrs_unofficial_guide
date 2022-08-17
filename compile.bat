@echo off
chcp 65001 >nul

set flag=%1
if %flag%x == x (
	set flag=qbook
)

if %flag%x == qbookx (
	call :cleanall
	call :qbook	
	if ERRORLEVEL 1 (
		echo Error! Please check the 'qbook.log' for more details...
		pause
	) else (
		call :clean
		echo Finished!
	)
	goto :EOF
)

if %flag%x == cleanx (
	call :clean
	goto :EOF
)

if %flag%x == cleanallx (
	call :cleanall
	goto :EOF
)

:help
	echo This is the compile batch script for Qbook.
	echo Usage:
	echo     compile.bat [option]
	echo options:
	echo   qbook    Compile the qbook (default)
	echo   clean     Clean all work files
	echo   cleanall  Clean all work files and qbook.pdf
	echo   help      Print this help message
goto :EOF

:qbook
	echo Compile...
	latexmk -xelatex -halt-on-error -silent qbook >nul 2>nul
goto :EOF

:clean
	echo Clean files...
	latexmk -c -silent 2>nul
	del tex\*.aux >nul 2>nul
goto :EOF

:cleanall
	echo Clean files...
	latexmk -C -silent 2>nul
	del tex\*.aux >nul 2>nul
	if exist qbook.pdf (
		echo Close the file: qbook.pdf!
		pause
		call :cleanall
	)
goto :EOF
