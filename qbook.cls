%# -*- coding: utf-8-unix -*-
%======================================================================
% qbook.cls for Qbook Template
%======================================================================
\NeedsTeXFormat{LaTeX2e}[1995/12/01]
\ProvidesClass{qbook}[2019/05/16 v2.01 Qbook Template]
\def\version{v2.01}
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{ctexbook}}
\ProcessOptions\relax
\PassOptionsToClass{scheme=chinese}{ctexbook}
\PassOptionsToClass{zihao=-4}{ctexbook}
\PassOptionsToPackage{no-math}{fontspec}
\LoadClass[a4paper,UTF8]{ctexbook}
%======================================================================
% 导入 qbook.cfg 文件
\AtEndOfClass{\input{qbook.cfg}} 
%======================================================================
% 导入 LaTeX 宏包
\RequirePackage{extarrows}
\RequirePackage{eso-pic}
\RequirePackage{url}
\RequirePackage{environ}
\RequirePackage{manfnt,pifont}
\RequirePackage{titlesec}
\RequirePackage{float}
\RequirePackage{wallpaper}
\RequirePackage[most]{tcolorbox}
\RequirePackage{xpatch}
\RequirePackage[centering,a4paper,body={16cm,22cm}]{geometry} 
\RequirePackage{fancyhdr}
\RequirePackage{lastpage}
\RequirePackage{amsmath,mathtools,amsthm,amsfonts,amssymb,bm}
\RequirePackage[defaultsups]{newtxtext}
\RequirePackage{newtxmath}
\RequirePackage{sourcecodepro}
\RequirePackage{upgreek}
\RequirePackage{wasysym}
\RequirePackage{anyfontsize}
\RequirePackage{metalogo,doc}
\RequirePackage{array}
\RequirePackage{threeparttable}
\RequirePackage{dcolumn}
\RequirePackage{multirow}
\RequirePackage{booktabs}
\RequirePackage{graphicx}
\RequirePackage[labelformat=empty]{caption}
\RequirePackage[list=off]{bicaption}
\RequirePackage{subcaption}
\RequirePackage[backend=biber, hyperref=auto,maxnames=4]{biblatex}
\RequirePackage{xcolor}
\RequirePackage{listings}
\RequirePackage[unicode, xetex, bookmarksnumbered, colorlinks, urlcolor=blue, linkcolor=purple, citecolor=red, plainpages=false, pdfstartview=FitH]{hyperref}
\RequirePackage{bookmark}
\bookmarksetup{
	open,	
	numbered
}
\RequirePackage{longtable}
\RequirePackage[perpage, bottom]{footmisc}
\RequirePackage[inline]{enumitem}
\RequirePackage{pdfpages}
\RequirePackage{calc}
\RequirePackage{algorithm, algorithmicx, algpseudocode}
\RequirePackage{siunitx}
\RequirePackage{tikz}
%======================================================================
% 导入tikz库
\usetikzlibrary{shapes.geometric, arrows}
\usetikzlibrary{shapes,decorations}
\usetikzlibrary{intersections,decorations.text}
%======================================================================
% 设置 PDF 文件信息
\hypersetup{
	pdfauthor = {333},
	pdftitle = {Q-book},
	pdfkeywords = {template}}
%======================================================================
% 汉化参考文献标题
\g@addto@macro\backmatter{
	\renewcommand{\em}{\itshape} % 书目部分以斜体表示强调	
	\renewcommand{\refname}{参考文献}
	\renewcommand{\bibname}{参考文献}
}
\DefineBibliographyStrings{english}{%
	in = {刊于},
	editor = {主编},
	byeditor = {编者为},
}
%======================================================================
% 添加水印
\newcommand{\watermark}[3]{\AddToShipoutPictureBG{
		\parbox[b][\paperheight]{\paperwidth}{
			\vfill%
			\centering%
			\tikz[remember picture, overlay]%
			\node [rotate = #1, scale = #2] at (8.5,-13)%
			{\textcolor{gray!80!cyan!30}{#3}};
			\vfill}}}
%======================================================================
% 自定义颜色
\definecolor{ocre}{RGB}{243,102,25} 
\definecolor{LightGoldenrod}{RGB}{238,221,130}
\definecolor{sthlmGreen}{RGB}{0,134,127}
\definecolor{Gold}{RGB}{255,215,0}
\definecolor{C1}{RGB}{32,88,153}
\definecolor{C2}{RGB}{218,222,238}
\definecolor{tssteelblue}{RGB}{0,40,220}
\definecolor{tsorange}{RGB}{255,138,88}
\definecolor{tsblue}{RGB}{23,74,117}
\definecolor{tsforestgreen}{RGB}{21,122,81}
\definecolor{tsyellow}{RGB}{255,185,88}
\definecolor{tsgrey}{RGB}{200,200,200}
\definecolor{main}{RGB}{0,120,2}
\definecolor{seco}{RGB}{230,90,7}%
\definecolor{thid}{RGB}{0,160,152}%
\definecolor{bule}{RGB}{18,29,57}
\definecolor{bablue}{RGB}{248,248,248}
\definecolor{c1}{RGB}{62, 97, 127}
\definecolor{c2}{RGB}{104, 182, 182}
\definecolor{c3}{RGB}{107, 190, 190}
\definecolor{c4}{RGB}{100, 172, 174}
\definecolor{c5}{RGB}{95, 162, 162}
%======================================================================
% 设置日期显示格式为yyyy-mm-dd
\def\twodigits#1{\ifnum#1<10 0\fi\the#1}
\renewcommand{\today}{\number\year-\twodigits\month-\number\day}
%======================================================================
\setcounter{secnumdepth}{4}  % 章节编号深度 (part 对应 -1)
\setcounter{tocdepth}{2}     % 目录深度 (part 对应 -1)
\newcolumntype{d}[1]{D{.}{.}{#1}}% or D{.}{,}{#1} or D{.}{\cdot}{#1}
%======================================================================
\newcommand{\cndash}{\rule{0.0em}{0pt}\rule[0.35em]{1.4em}{0.05em}\rule{0.2em}{0pt}}
\newcommand{\ch}{\titleformat{\chapter}[display]{\centering}{}{-3mm}{\Huge\bfseries}
	\titlespacing{\chapter}{0pt}{0pt}{2\baselineskip}}%用来将需要的章节标题居中
%======================================================================
% 行距缩放因子
\linespread{1.3}
%======================================================================
% 设置名称：目录、表格索引、插图索引
\ctexset{contentsname={\q@contentsname}}
\ctexset{listfigurename={\q@listfigurename}}
\ctexset{listtablename={\q@listtablename}}
\renewcommand{\lstlistingname}{\q@value@listingname}
%======================================================================
% 定制章节样式
\titleformat{\chapter}[display]{\flushleft}{
	\begin{tikzpicture}
	\node[anchor=south west] (chap) at (0.1,1.3){\fontsize{96pt}{96pt}\bfseries\thechapter};
	\path [left color=C1,right color=C2] (0,1) rectangle (\textwidth,0);
	\path(0,-0.2); 
	\end{tikzpicture} 
}{-3mm}{\Huge\bfseries}
\titlespacing{\chapter}{0pt}{0pt}{2\baselineskip}
%======================================================================
% section级样式设置
\ctexset{section={
	format={\color{tssteelblue}\large\bfseries},
	afterskip={1.0ex \@plus .2ex},
	}
}
%======================================================================
% subection级样式设置
\ctexset{subsection={
	format={\color{tssteelblue}\bfseries\normalsize},
	indent={0\ccwd},
	afterskip={1.0ex \@plus .2ex},
	}
}
%======================================================================
% subsubection级样式设置
\ctexset{subsubsection={
	format={\normalfont\normalsize},
	indent={0\ccwd},
	afterskip={1.0ex \@plus .2ex},
	}
}
%======================================================================
% 设置item条目的索引符号为bullet
\renewcommand{\labelitemi}{\ensuremath{\RHD}}
%======================================================================
% 设置图片载入路径及扩展名
\graphicspath{{fig/}{figure/}{figures/}{logo/}{logos/}{graph/}{graphs}}
\DeclareGraphicsExtensions{.pdf,.eps,.png,.jpg,.jpeg}
%======================================================================
% 设置图片的标题样式
\DeclareCaptionFont{kaishu}{\kaishu}
\captionsetup{format=plain,labelformat=simple,labelsep=space,justification=centering,font={small,kaishu}}
\captionsetup[sub]{font=footnotesize}
\DeclareCaptionOption{bi-first}[]{
    \def\tablename{\q@tablename}
    \def\figurename{\q@figurename}
}
\DeclareCaptionOption{bi-second}[]{
    \def\tablename{Table}
    \def\figurename{Figure}
}
\captionsetup[bi-first]{bi-first}
\captionsetup[bi-second]{bi-second}
%======================================================================
% Set fontnote font size in threeparttable
\appto\TPTnoteSettings{\footnotesize}
%======================================================================
% 浮动参数
\renewcommand{\textfraction}{0.15}
\renewcommand{\topfraction}{0.85}
\renewcommand{\bottomfraction}{0.65}
\renewcommand{\floatpagefraction}{0.60}
%======================================================================
% 定理、公式、图、表的编号为"3.1"的形式
\renewcommand{\theequation}{\arabic{chapter}.\arabic{equation}}
\renewcommand{\thefigure}{\arabic{chapter}--\arabic{figure}}
\renewcommand\p@subfigure{\thefigure}
\renewcommand{\thetable}{\arabic{chapter}--\arabic{table}}
\AtBeginDocument{\renewcommand{\thelstlisting}{\arabic{chapter}--\arabic{lstlisting}}}
%======================================================================
% 使用enumitem宏包配制列表环境
\setlist{nosep}  % 紧凑间距
\setlist*{leftmargin=*}  % 列表和段落头对齐
\setlist[1]{labelindent=\parindent} % Only the level 1
%======================================================================
% 设置宏包 listings/lstlistings
\lstset{tabsize=4, %
  frame=shadowbox,  %把代码用带有阴影的框圈起来
  commentstyle=\color{red!50!green!50!blue!50},  %浅灰色的注释
  rulesepcolor=\color{red!20!green!20!blue!20},  %代码块边框为淡青色
  keywordstyle=\color{blue!90}\bfseries,  %代码关键字的颜色为蓝色，粗体
  showstringspaces=false,  %不显示代码字符串中间的空格标记
  stringstyle=\ttfamily,  % 代码字符串的特殊格式
  keepspaces=true,   %
  breakindent=22pt,  %
  numbers=left,  %左侧显示行号
  stepnumber=1,  %
  numberstyle=\tiny,  %行号字体用小号
  basicstyle={\footnotesize\ttfamily},  %
  showspaces=false,  %
  flexiblecolumns=true,  %
  breaklines=true,  %对过长的代码自动换行
  breakautoindent=true, %
  breakindent=4em,  %
  aboveskip=1em,  %代码块边框
  fontadjust,
  captionpos=t,
  framextopmargin=2pt,framexbottommargin=2pt,abovecaptionskip=-9pt,belowcaptionskip=9pt,
  xleftmargin=4em,xrightmargin=4em,  % 设定listing左右的空白
  texcl=true,
  % 设定中文冲突，断行，列模式，数学环境输入，listing数字的样式
  extendedchars=false,columns=flexible,mathescape=true
  numbersep=-1em
}
%======================================================================
% Setting Package siunitx
\sisetup{detect-all} % Detecting fonts
%======================================================================
% 定制定理、定义、观察、规则、keypoint环境
 \tcbset{
 	commondef/.style={
 		fontupper=\kaishu,
 		lower separated=false,
 		coltitle=white,
 		colback=yellow!20,
 		fonttitle=\heiti\bfseries,
 		enhanced,
 		breakable,
 		top=10pt,
 		left=8pt,
 	%	bottom=6pt,
 		before skip=8pt,
 		attach boxed title to top left={yshift=-0.11in,xshift=0.15in},
 		boxed title style={boxrule=0pt,colframe=white,arc=0pt,outer arc=0pt},
 	},
 	commonthm/.style={
 		fontupper=\kaishu,
 		lower separated=false,
 		coltitle=white,
 		colback=blue!10,
 		fonttitle=\heiti\bfseries,
 		enhanced,
 		breakable,
 		top=10pt,
 	%	bottom=6pt,
 		before skip=8pt,
 		attach boxed title to top left={yshift=-0.11in,xshift=0.15in},
 		boxed title style={boxrule=0pt,colframe=white,arc=0pt,outer arc=0pt},
 	},
 	common/.style={
 		fontupper=\kaishu,
 		lower separated=false,
 		coltitle=white,
 		colback=gray!10,
 		fonttitle=\heiti\bfseries,
 		enhanced,
 		breakable,
 		top=10pt,
 	%	bottom=6pt,
 		before skip=8pt,
 		attach boxed title to top left={yshift=-0.11in,xshift=0.15in},
 		boxed title style={boxrule=0pt,colframe=white,arc=0pt,outer arc=0pt},
 	},
 	defstyle/.style={
 		commondef,
 		colframe=seco,  
 		colbacktitle=seco, 
 		overlay unbroken and last={\node[anchor=south east, outer sep=6pt] at (\textwidth-width,0) {\textcolor{seco}{$\clubsuit$}}; },
 		separator sign none
 	},
 	thmstyle/.style={
 		common,
 		colframe=main,  
 		colbacktitle=main, 
 		overlay unbroken and last={\node[anchor=south east, outer sep=6pt] at (\textwidth-width,0) {\textcolor{main}{$\heartsuit$}}; },
 		separator sign none
 	},
 	propstyle/.style={
 		common,
 		colframe=thid,  
 		colbacktitle=thid, 
 		overlay unbroken and last={\node[anchor=south east, outer sep=6pt] at (\textwidth-width,0) {\textcolor{thid}{$\spadesuit$}}; },
 		separator sign none
 	},
 }

\newtcbtheorem[auto counter,number within=chapter]{mydef}{\q@label@defn}{defstyle}{def}
\newtcbtheorem[use counter from=mydef]{mythm}{\q@label@thm}{thmstyle}{thm} 
\newtcbtheorem[use counter from=mydef]{myprop}{\q@label@prop}{propstyle}{prop} 
\newtheorem{keypoint}{\q@label@keypoint}[chapter]  %环境名keypoint

\newtheorem{observation}[tcb@cnt@mydef]{{\makebox[0pt][r]{\scriptsize\color{red!90}\textdbend\quad}\textbf{\q@label@rem}}}

\newenvironment{remark}   
{\begin{observation}} {\end{observation}}
%======================================================================
% 引用样式为“图x.y”等
\newcommand{\requ}[1]{(\ref{#1})}
\newcommand{\rremark}[1]{\text{{\color{purple}{注}}} \ref{#1}}
\newcommand{\rfig}[1]{\text{{\color{purple}{图}}} \ref{#1}}
\newcommand{\rtab}[1]{\text{{\color{purple}{表}}} \ref{#1}}
\newcommand{\rprop}[1]{\text{{\color{purple}{性质}}} \ref{#1}}
\newcommand{\rdef}[1]{\text{{\color{purple}{定义}}} \ref{#1}}
\newcommand{\rthm}[1]{\text{{\color{purple}{定理}}} \ref{#1}}
\newcommand{\mylem}[1]{\text{引理} \ref{#1}}  
\newcommand{\rexa}[1]{\text{{\color{purple}{例}}} \ref{#1}}
\renewcommand{\proofname}{\bfseries\q@label@proof}  
%======================================================================
% 设置页眉与页脚样式
\newcommand\q@fancyhead{\small\kaishu}
\def\markboxwidth{0.75\textwidth}
\pagestyle{fancy}
\fancyhf{} 
\fancyhead[LE,RO]{\sffamily\normalsize\thepage}  %在奇数页的右上角显示页码，偶数页的左上角显示页码
\fancyhead[LO]{\nouppercase{\q@fancyhead\rightmark}} % 在奇数页的左侧显示小节名
\fancyhead[RE]{\nouppercase{\q@fancyhead\leftmark}}  % 在偶数页的右侧显示章名  
\renewcommand{\headrulewidth}{0.5pt} 
\addtolength{\headheight}{2.5pt} 
\renewcommand{\footrulewidth}{0pt} 
\fancypagestyle{plain}{\fancyhead{}\renewcommand{\headrulewidth}{0pt}} 
%======================================================================
% Removes the header from odd empty pages at the end of chapters
\makeatletter
\renewcommand{\cleardoublepage}{
	\clearpage\ifodd\c@page\else
	\hbox{}
	\vspace*{\fill}
	\thispagestyle{empty}
	\newpage
	\fi}
%======================================================================
% 前言
\newenvironment{pre}{
	\ch\chapter{\q@pre}{}}{}
%======================================================================
% 概览
\newenvironment{overview}{
\ch\chapter{\q@overviewname}{}}{}
%======================================================================
% 设置目录
\renewcommand\tableofcontents{%
  \cleardoublepage
  \pdfbookmark[0]{\contentsname}{toc}
  \chapter*{\centerline{\contentsname}}
  \@mkboth{\MakeUppercase\contentsname}{\MakeUppercase\contentsname}%
  \@starttoc{toc}%
}
\addtocontents{toc}{\let\string\CTEX@spaceChar\relax}
%======================================================================
%定制example环境
\RequirePackage[framemethod=default]{mdframed} 
% Example box
\newmdenv[skipabove=5pt,
skipbelow=7pt,
rightline=false,
leftline=true,
topline=false,
bottomline=false,
backgroundcolor=sthlmGreen!5,
linecolor=sthlmGreen,
innerleftmargin=0.5pt,
innerrightmargin=0pt,
innertopmargin=0pt,
innerbottommargin=0pt,
leftmargin=0cm,
rightmargin=0cm,
linewidth=1pt]{exaBox}
\newtheoremstyle{blacknumexa}% Theorem style Example
{5pt}% Space above
{5pt}% Space below
{\kaishu}% Body font
{} % Indent amount
{\small\bf\kaishu\color{sthlmGreen}}% Theorem head font
{\;}% Punctuation after theorem head
{0.25em}% Space after theorem head
{\small\sffamily\color{sthlmGreen}\thmname{#1}\nobreakspace\thmnumber{\@ifnotempty{#1}{}\@upn{#2}}% Theorem text (e.g. Theorem 2.1)
	\thmnote{\nobreakspace\the\thm@notefont\heiti\color{sthlmGreen}\nobreakspace(#3)}}% Optional

\theoremstyle{blacknumexa}
\newtheorem{exampleT}[tcb@cnt@mydef]{例}
\newenvironment{example}{\begin{exaBox}\begin{exampleT}}{\hfill{\color{sthlmGreen}}\end{exampleT}\end{exaBox}}
%======================================================================
%定制例子中的横线
\newcommand{\cGreen}[1]{{\color{sthlmGreen}{#1}}}
\newcommand{\soln}[1]{\par\vspace{1.5pt}\makebox[5pt]{\begin{tikzpicture}[overlay]
		\node at (-15pt,0pt){\textcolor{sthlmGreen}{\ding{45}}};\end{tikzpicture}}\cGreen{\noindent\hrulefill\vskip 1pt}}
%======================================================================
\endinput