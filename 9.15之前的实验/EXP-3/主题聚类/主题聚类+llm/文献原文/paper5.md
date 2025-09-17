# 飞机健康管理平台的客户需求分析与 PLM 服务资源匹配

和伟辉1，明新国1，刘 安2，郑茂宽( 1．上海交通大学 机械与动力工程学院，上海 200240，E-mail: 18817558023@ 163．com;2．西安卫星测控中心，西安 710043)

摘 要: 根据对航空系统各个相关利益方的需求分析，基于模糊理论确立飞机故障诊断和健康管理( Prognostic and Health Management，PHM) 平台的各个模块需实现的功能，利用灰色关联法对客户需求进行重要度排序，并基于自回归求和移动平均( ARIMA) 模型求解客户需求的动态特征，对客户需求作出全面的分析和预期。最终在质量屋( House of Quality，HOQ) 衡量全生命周期管理( Product Lifecycle Management，PLM) 的服务资源与客户需求的匹配度，进而定量反映客户对航空系统各种服务资源的满意度。

关键词: 故障诊断和健康管理; 需求分析; 灰色关联法; ARIMA; 服务资源配置中图分类号: TP277 文献标识码: ADOI:10.13952/j.cnki.jofmdr.2018.0217

# Customer Needs Analysis of Aircraft PHM Platform and PLM Service Resources Mapping

HE Weihui1，MING Xinguo1，LIU $\mathrm { A n } ^ { 2 }$ ，ZHENG Maokuan1 ( 1．School of Mechanical Engineering，Shanghai Jiao Tong University，Shanghai 200240，China;

2．Xi’an Satellite Control Ceter，Xi’an 710043，China)

Abstract: According to the demand analysis of each stakeholder in the aviation system，the functions realized in each module of aircraft Prognostic and Health Management( PHM) platform are establishedbased on fuzzy theory．Using gray relational analysis to sort customer needsand analyzing the dynamic characteristics of customer needs based on the ARIMA model to fully analyze and anticipate customer needs． Finally，House of Quality ( HOQ) measures the matching degree of Product Lifecycle Management ( PLM ) service resources with customer needs to quantitatively reflect customer satisfaction with various service resources of the aviation system．

Key words: prognostic and health management; needs analysis; gray relational analysis; ARIMA; service resource mapping

为确保飞机健康、经济运行，及早发现并解决故障，合理安排维护时间，缩短飞机停机时间，降低运营和服务成本，通过提高飞机可用性以增加收入。国际上，飞机故障诊断与健康管理( Prognostic and Health Management，PHM) 平台业已成为航空业着力发展的研究领域［1］，比如波音 777 的 AHM 系统、空客A380 的AIRMAN 系统、加拿大国家研究委员会研制的飞机综合诊断系统( IDS) 等。因此对飞机 PHM 平台的客户需求分析，以及对客户需求与企业 PLM 的服务资源映射关系的研究就显得尤其重要。

在客户需求研究中，客户需求信息难以定量描述和客户缺乏产品的专业性知识，导致企业难以把握客户的真正需求，造成企业在工程实践上与客户存在理解偏差，最终影响企业的生存发展; 另一方面，企业在客户基本需求基础上，如何深层次地发掘需求信息，提升产品性能，进行客户需求信息的区分和判定，亟需科学有效的分析方法。目前，针对需求分析的方法，国内外学者已进行了大量的研究包括隐性需求以及动态需求的分析，基于 KANO 模型挖掘客户的兴奋型需求，Kahraman等通过模糊质量功能配置( Quality Function Deployment，QFD)确定产品技术需求［2－3］。但尚缺乏针对飞机 PHM 平台的需求分析以及需求向生命周期管理( Product Lifecycle Management，PLM) 的服务资源的映射方法的研究。因此本文建立了飞机PHM 平台的客户需求获取与推理总体框架，以及基于灰色关联法的需求分析和基于ARIMA 的动态预测，并通过质量屋( Houseof Quality，HOQ) 完成需求向PLM 的服务资源映射，从而为飞机PHM 平台设计和搭建提供基础。

# 1 飞机 PHM 平台的客户需求获取与推理总体框架

本文针对飞机服务方在整个航空系统中相关利益方涵盖范围广且产品种类具有的复杂性和多样性的特点，提出以下飞机 PHM 平台的客户需求获取与推理研究框架，用于建立客机故障诊断与健康管理服务平台系统的功能定义。如图 1 所示。首先，对相关利益方进行完整的需求分析，通过灰色系统理论对需求种类进行重要度排序。

![](images/aabc7874d375d54bc75fac716c08a5524f88b87132667502c771a27c7ea7df08.jpg)  
▲图1 飞机 PHM 平台的客户需求获取与推理研究框架

进一步观测搜集平台某个功能模块的点击率、访客数、访客属性、计算资源负荷、平均访问时长、流量占比等数据，根据需求的静态特征，通过自回归求和移动平均 ARIMA 模型计算即可定量分析预测未来某时刻用户对平台的需求，便于软、硬件资源的分配和调整，通过对智能交互采集来的信息进行提炼，评价功能子模块的优劣，指导平台的下一步完善。

最终，用模糊度量方法对客户需求及面向全生命周期管理的企业服务资源进行重要度排序，实现通过 QFD 构建面向 PLM 的客户需求向服务资源映射的配置模型，进而完成各种服务资源对客户需求满意度的反馈机制。

# 2 相关利益方分析

在整个航空系统中，飞机服务方的相关利益方涵盖对象复杂，主要包括机场、航空公司、飞机设计方、飞机制造商、 $x$ 行员 5 大方面。每个相关利益方的基本业务需求为: $\textcircled{1}$ 机场方面: 机场排班调度，应急响应，机务维修，航材支援等; $\textcircled{2}$ 航空公司方面: 机队管理，飞机健康管理，航材服务，维修服务，飞行计划等 $\textcircled{3}$ 飞机设计方方面: 飞机关键部件寿命分析， $x$ 机动力性能参数分析，飞机航电系统故障数据，飞机发动机运行数据，飞机结构性能历史数据，飞机燃油消耗历史数据等; $\textcircled{4}$ 飞机制造商方面与设计方基本一致; $\textcircled{5}$ 飞行员方面: $x$ 行数据分析( 驾驶行为习惯、操作熟练程度、误操作分析等) ，飞机辅助驾驶，飞行训练，飞行手册( 知识服务) ，故障提醒/误操作提醒等［4］。

# 3 需求分析

# 3．1 客户需求重要度分析

通过对所有客户需求的归类，方便进一步划分每个子模块的功能。由于对于需求的分类具有模糊性，所以，常常使用模糊理论对不同客户需求进行分类［5］。

设用户需求有 $m$ 个， $\mathcal { L } R = \{ \ C R _ { 1 } ~ , C R _ { 2 } ~ , \cdots ~ , C R _ { n } ) ^ { \mathrm { ~ T ~ } } \ \mathcal { L } R _ { i }$ 代表用户的第 $i$ 个需求，若需求按一定特性分类为 $n$ 个类别， $\mathcal { L } R _ { i j }$ 在［0，1］区间内取值，表示第 $i$ 个用户需求与第 $j$ 类特征需求的关联度，取值越大，说明此需求隶属于第 $j$ 类特征需求的程度越高，所以用户需求的矩阵表示形式为:

$$
C R = \left( \begin{array} { c c c c } { { C R _ { 1 1 } } } & { { C R _ { 1 2 } } } & { { \cdots } } & { { C R _ { 1 n } } } \\ { { \vdots } } & { { \vdots } } & { { \ddots } } & { { \vdots } } \\ { { C R _ { m 1 } } } & { { C R _ { m 2 } } } & { { \cdots } } & { { C R _ { m n } } } \end{array} \right)
$$

模糊相似矩阵的建立:

$$
r _ { i k } \ = \ 1 \ - c \sum _ { j = 1 } ^ { n } \ \mid C R _ { i j } \ - C R _ { k j } \ \mid \ A \ i \ k \ = \ 1 \ 2 \ \cdots \ m )
$$

$C$ 为修正系数，取值 0 到 1 之间，第 $\mathbf { \chi } _ { i }$ 项客户需求与第 $k$ 项客户需求相似度越高， $, r _ { i k }$ 取值越大，等于 0 时说明没有相似度，等于 1 时，说明两项需求属于同类。通过求解模糊相似矩阵的传递闭包 $T$ ，作为用户需求分类的依据。

对分类后的用户需求用灰色关联法求解需求重要度排序［6］，步骤如下:

( 1) $C R _ { j } = ( \ C R _ { 1 } \ , C R _ { 2 } \ , \cdots \ , C R _ { n } ) ^ { \mathrm { ~ T ~ } }$ ，通过同 1 行需求的取值( 即某个需求与 $\mathbf { \Omega } _ { n }$ 类特征需求的所有关联度) 来区间值化，当目标望大时，处理方式为:

$$
C R _ { i j } ^ { * } \ = \frac { C R _ { i j } - \operatorname * { m i n } _ { i = 1 } ^ { m } ( \ C R _ { i j } ) } { \operatorname * { m a x } _ { i = 1 } ^ { m } ( \ C R _ { i j } ) \ - \operatorname * { m i n } _ { i = 1 } ^ { m } ( \ C R _ { i j } ) } \ ,
$$

$$
( \textit { i } = 0 \mathrm { ~ , ~ } 1 \mathrm { ~ } 2 \mathrm { ~ , ~ } ^ { \dots } \mathrm { ~ } m \textit { j } = 0 \mathrm { ~ , ~ } 1 \mathrm { ~ } 2 \mathrm { ~ , ~ } ^ { \dots } \mathrm { ~ } n )
$$

( 2) 求差序列

$$
\begin{array} { c } { \Delta j _ { i } \ = \ \vert \ C R _ { 0 j } ^ { * } \ - C R _ { i j } ^ { * } \ \vert \ , } \\ { ( \ i \ = \ 0 \ , 1 \ 2 \ , \cdots \ m \ j \ = \ 0 \ , 1 \ 2 \ , \cdots \ n ) } \end{array}
$$

( 3) 求两级的最大差和最小差

$$
\begin{array} { r } { \Delta _ { \operatorname* { m a x } } = \operatorname* { m a x } _ { \forall i } \operatorname* { m a x } _ { \forall j } ( \Delta j _ { i } ) } \\ { \Delta _ { \operatorname* { m i n } } = \operatorname* { m i n } _ { \forall i } \operatorname* { m i n } _ { \forall j } ( \Delta j _ { i } ) } \end{array}
$$

( 4) 计算关联系数

$$
\gamma _ { i } ( j ) = \frac { \Delta _ { \operatorname* { m i n } } + \xi \Delta _ { \operatorname* { m a x } } } { \Delta j _ { i } + \xi \Delta _ { \operatorname* { m a x } } }
$$

$\xi \in [ 0 \mathrm { ~ , 1 ] ~ }$ 为给定的分辨系数，一般取值为 0．5

( 5) 计算客户需求的相对重要度

$$
g _ { i } \ = \ \frac 1 n \sum _ { j \ = 1 } ^ { n } \ \omega _ { j } \ \gamma _ { i } ( j ) , \ \sum _ { j \ = \ 1 } ^ { n } \ \omega _ { j } \ = \ 1
$$

式中: $\omega _ { j }$ 为客户需求所属类别的重要程度， $\boldsymbol { \mathscr { g } } _ { i }$ 即为衡量每项需求重要度的计算结果。

# 3．2 客户动态需求分析

然而，仅根据客户某个时间点的需求分析对平台作出的设计，无法满足需求的动态变化特性和后期平台的持续改进和调整。时间序列分析方法通过寻求 1 段时间内观测数据的发展变化特征，进而预测未来的某个时刻观测量的数值，能有效预测决定平台下 1 步需要重点维护和改进的功能。非平稳时间序列模型—ARIMA( $\textit { p d } \boldsymbol { q } )$ 模型其中 $p$ 为自回归项， $\mu$ 为时间序列平稳化所需的差分次数， $q$ 为移动平均项数，使用 ARIMA 模型前，首先应计算自相关系数 ACF、偏自相关系数 PACF 以便确定模型，本文使用 SPSS 进行检验。通过适当差分得到平稳( 即均值、方差、协方差是与时间 t 无关的常数) 时间序列 $\mathrm { A R M A } ( \mathbf { \Sigma } _ { P } \mathbf { \Sigma } , q )$ ，其中 AR 是自回归模型，MA 为移动平均模型。设 $\{ X _ { t } \}$ 为原始观测所得的非平稳序列，通过 d 阶差分得到 7 :

$$
Y _ { t } \ = \ \nabla ^ { d } \ X _ { t } \ = \ ( \ 1 \ - B ) ^ { \ d } \ X _ { t } \ = \ \sum _ { i = 0 } ^ { d } \ ( \ - \ 1 ) ^ { \ i } \ C _ { d } ^ { i } X _ { t - i }
$$

此时， $, Y _ { t }$ 服从一般平稳 ARMA( $_ { p } \mathinner { \lrcorner } q )$ 过程，即 $\varphi _ { p } ( \textit { B } ) \textit { Y } _ { t } =$ $\theta _ { q } ( \boldsymbol { B } ) \varepsilon _ { t }$

则模型具体表达式为:

$$
\left. { \begin{array} { l } { \varphi _ { p } ( B ) \nabla ^ { d } X _ { t } = \theta _ { q } ( B ) \varepsilon _ { t } } \\ { E ( \varepsilon _ { t } ) = 0 , { V a r } ( \varepsilon _ { t } ) = \sigma _ { \varepsilon } ^ { 2 } , E ( \varepsilon _ { t } \varepsilon _ { s } ) = 0 , ( s \neq t ) } \\ { E X _ { s } \varepsilon _ { t } = 0 , { \ V } \lor s < t ) } \end{array} } \right\}
$$

式中: $B$ 为延迟算子，用于简化模型的表达式，其定义为: $B X _ { t }$ $\scriptstyle = X _ { t - 1 }$ ，算子 $B$ 有性质:

$$
B ^ { 0 } \ = \ 1 \ B ^ { k } \ X _ { t } \ = \ X _ { t - k }
$$

平稳 $A R ($ 前 $p$ 个时间点的 $X$ 值自回归) 算子:

$$
\varphi _ { p } ( B ) = 1 - \varphi _ { 1 } B - \varphi _ { 2 } B ^ { 2 } - \cdots - \varphi _ { p } B ^ { p }
$$

可逆 $M A ($ 前 $q$ 个时间点的残差值滑动平均) 算子:

$$
\theta _ { q } ( B ) \ = \ 1 \ - \theta _ { 1 } B - \theta _ { 2 } \ B ^ { 2 } \ - \ \cdots \ - \ \theta _ { q } \ B ^ { q }
$$

通过 ARIMA 模型提前预测服务资源平台对于客户需求的承载能力是过剩还是不足，进而做出软、硬件资源的分配和调整，增强平台对客户需求的动态响应能力，对平台进一步改进设计具有指导意义。

# 4 需求到服务资源的映射

航空客服企业具备的服务资源包括: $\textcircled{1}$ 向客户提供飞机抢修、改装等工程技术支援，为客户提供维修方案支援，开展整机和部/附件维修，建立飞机工程技术支援和维护/维修支援网络以及维修工程师。 $\textcircled{2}$ 航材备品备件［8］，包括为客户供给全天候飞机航线维护、维保修理、改装等业务所需的航材支援服务; 开展航材采购和飞机待件停场航材支援等工作;创建全球航材供应网络，提供网上咨询、订购及其它客户化航材支援服务。 $\textcircled{3}$ 培训资料，涵盖飞行训练、乘务训练、性能工程师训练。 $\textcircled{4}$ 计算中心: 包括系统与部件的寿命估计、可靠性计算。 $\textcircled{5}$ 云平台: 包括实时监控、故障诊断、维修决策、健康评估等综合服务。 $\textcircled{6}$ 数据库: 包括飞机航行信息、飞机状态参数等数据。 $\textcircled{7}$ 传感网络: 包括飞机空调系统、电源系统、飞控系统、燃油系统、液压系统、防冰除雨系统、起落架系统、引气系统以及 APU 系统等状态检测传感器网络［9］。 $\textcircled{8}$ 知识库: 包括故障隔离手册、诊断规则知识库、维保记录等。

传统的 QFD 是将客户需求转化成功能特性、设计要求等要素的分析工具［10－11］，完整质量屋包括一下要素: $\textcircled{1}$ 客户需求; $\textcircled{2}$ 需求重要性; $\textcircled{3}$ 产品特性; $\textcircled{4}$ 客户需求与产品特性之间的关系; $\textcircled{5}$ 产品特性之间的关联矩阵; $\textcircled{6}$ 计划矩阵; $\textcircled{7}$ 目标值矩阵。有助于理清相对模糊的客户需求和工程设计之间的关联，有助于更好满足客户，提高产品的品质。文献［12］利用 QFD 实现企业的产品资源特性与需求的映射，本文利用 QFD 的这些优点，使用 HOQ 表征了客户需求与企业服务资源的匹配关系，有针对性地将飞机客服公司众多利益相关方纷繁复杂的需求和企业全生命周期管理的服务资源用工程语言表达出来，便于服务平台的设计和搭建，对企业提高服务质量、减少平台研发建设周期、收缩成本、提升客户满意度有重要意义。

综合上文对需求和全生命周期的服务资源的分析，通过飞机客服公司工程师对客户需求与服务资源关联度的评价得到关联矩阵。服务资源匹配度:

$$
S _ { j } ~ = ~ \sum ~ r _ { i j } ~ \cdot ~ w _ { i }
$$

式中: $r _ { i j }$ 为需求与服务的关联矩阵， ${ \mathbf { \nabla } } _ { \mathcal { W } _ { i } }$ 为客户需求的权重， $\mathbf { \Xi } _ { \mathcal { A } }$ 为客户需求编号，j 为服务资源编号［13］。

据前文对需求重要度的分析计算，通过灰色关联法确定客户需求的权重，再根据前文对客户动态需求的分析通过ARIMA 模型进行动态预测，不断对需求的重要度 $\boldsymbol { w } _ { i }$ ( 取值1～10) 以及服务资源 QFD 模型的关联矩阵 $\dot { \boldsymbol { \cdot } } \boldsymbol { r } _ { i j } ($ 取值 1、3、5) 进行调整，更新相应的服务匹配度，最终根据公式( 13) 计算服务资源匹配度 $S _ { j }$ ，持续改进飞机 PHM 平台以及企业 PLM 服务资源的配置。建立 HOQ 结构如图 2 所示。

![](images/f48f3ce053921492327ffeea8ce54848451d2de3b523359824425e7a18c45e7d.jpg)  
▲图2 需求向服务资源映射 HOQ 结构

相对于传统 QFD 矩阵，将产品特性转换为了服务资源，进而搭建了服务资源向客户需求的映射关系，并建立服务资源评估矩阵，通过 ARIMA 预测值调整需求重要度( 计划矩阵) 来增强服务资源匹配的动态特性。

# 5 实例验证

以飞机健康管理平台为例，按前文所述理论进行需求分析。飞机 PHM 系统在系统层面结合前文相关利益方分析可划分为“实时监控”、“故障诊断”、“维修决策”、“健康评估”4个功能模块。 $\textcircled{1}$ 实时监控功能单元主要实现: 实时显示飞机航行信息、实时飞机状态参数、实时故障监控; $\textcircled{2}$ 故障诊断功能单元主要实现: 故障信息和故障来源、FMECA/FTA、故障影响范围与严重等级 $\textcircled{3}$ 维修决策功能单元主要实现: 故障隔离手册、飞机维护历史记录( 故障案例库) 、诊断规则知识库$\textcircled{4}$ 健康评估功能单元主要实现: 飞机维保记录、系统与部件寿命估计、系统可靠性评估。

第 1 步，收集 100 名工程师对各项功能模块与需求匹配的关联度进行评价，汇总得到关联度矩阵，如表 1 所示。

表 1 需求关联度矩阵  

<html><body><table><tr><td>客户需求</td><td>实时监控</td><td>故障诊断</td><td>维修决策</td><td>健康评估</td></tr><tr><td>飞机航行 信息</td><td>0.8</td><td>0.4</td><td>0.2</td><td>0.1</td></tr><tr><td>飞机状态 参数</td><td>0.9</td><td>0.6</td><td>0.5</td><td>0.6</td></tr><tr><td>实时故障 监控</td><td>0.7</td><td>0.9</td><td>0.6</td><td>0.3</td></tr><tr><td>FMECA/FTA</td><td>0.4</td><td>0.8</td><td>0.7</td><td>0.2</td></tr><tr><td>故障隔离 手册</td><td>0.3</td><td>0.7</td><td>0.7</td><td>0.2</td></tr><tr><td>诊断规则 知识库</td><td>0.1</td><td>0.8</td><td>0.6</td><td>0.1</td></tr><tr><td>飞机维保 记录</td><td>0.1</td><td>0.4</td><td>0.5</td><td>0.6</td></tr><tr><td>系统与部件 寿命估计</td><td>0.3</td><td>0.2</td><td>0.1</td><td>0.7</td></tr><tr><td>系统可靠 性评估</td><td>0.4</td><td>0.2</td><td>0.1</td><td>0.8</td></tr></table></body></html>

# 求解得到，传递闭包 T。

<html><body><table><tr><td rowspan="7">T=</td><td>1</td><td colspan="3">0.56 0.56 0.56 0.56 0.56 0.56 0.56</td></tr><tr><td>0.56 1</td><td>0.64 0.64</td><td>0.64 0.64</td><td>0.60 0.60 0.60</td></tr><tr><td>0.56</td><td>0.64 1 0.76</td><td>0.76 0.76</td><td>0.60 0.60 0.60</td></tr><tr><td>0.56</td><td>0.64 0.76</td><td>1 0.92 0.80</td><td>0.60 0.60 0.60</td></tr><tr><td>0.56</td><td>0.64 0.76</td><td>0.92 1 0.80</td><td>0.60 0.60 0.60</td></tr><tr><td>0.56 0.64</td><td>0.76 0.80</td><td>0.80 1</td><td>0.60 0.60 0.60</td></tr><tr><td>0.56 0.60</td><td>0.60 0.60</td><td>0.60 0.60</td><td>1 0.64 0.64</td></tr><tr><td>0.56 0.56</td><td>0.60 0.60</td><td>0.60 0.60</td><td>0.60 0.64 1 0.92</td></tr><tr><td>0.60 0.60</td><td>0.60</td><td>0.60 0.60</td><td>0.64 0.92 1</td></tr></table></body></html>

$\lambda$ 取 0．92 时，可以分为:

$$
\{ \ C R _ { 1 } \} \{ \ C R _ { 2 } \} \{ C R _ { 3 } \} \{ C R _ { 4 } \ C R _ { 4 } \ C R _ { 5 } \} \{ C R _ { 6 } \} \{ C R _ { 7 } \} \{ C R _ { 8 } \ C R _ { 9 } \}
$$

$\lambda$ 取 0．80 时，可以分为:

$$
\{ C R _ { 1 } \} \{ C R _ { 2 } \} \{ C R _ { 3 } \} \{ C R _ { 3 } \} \{ C R _ { 4 } \ C R _ { 5 } \ C R _ { 6 } \} \{ C R _ { 7 } \} \{ C R _ { 8 } \ C R _ { 9 } \}
$$

$\lambda$ 取 0．76 时，可以分为:

$\{ C R _ { 1 } \} \{ C R _ { 2 } \} \{ C R _ { 3 } \ C R _ { 4 } \ C R _ { 5 } \ C R _ { 6 } \} \{ C R _ { 7 } \} \{ C R _ { 8 } \ C R _ { 9 } \}$ $\lambda$ 取 0．64 时，可以分为:$\{ C R _ { 1 } \} \ { \ } { \ } { \ } \ C R _ { 2 } \ C R _ { 3 } \ C R _ { 4 } \ C R _ { 5 } \ C R _ { 6 } \} \ { \ } \ { \downarrow C R _ { 7 } } \ C R _ { 8 } \ C R _ { 9 } \}$ $\lambda$ 取 0．60 时，可以分为:$\{ C R _ { 1 } \} \{ C R _ { 2 } , C R _ { 3 } , C R _ { 4 } , C R _ { 5 } , C R _ { 6 } , C R _ { 7 } , C R _ { 8 } , C R _ { 9 } \}$ $\lambda$ 取 0．56 时，可以分为:

$$
\{ C R _ { 1 } ~ , C R _ { 2 } ~ , C R _ { 3 } ~ , C R _ { 4 } ~ , C R _ { 5 } ~ , C R _ { 6 } ~ , C R _ { 7 } ~ , C R _ { 8 } ~ , C R _ { 9 } \}
$$

$\lambda$ 取 0．76 时，对 $\{ C R _ { 3 } \ C R _ { 4 } \ C R _ { 5 } \ C R _ { 6 } \}$ 这 4 项关联度较高的需求重要度进行排序:

当 $\mathbf { \widetilde { j } } \omega _ { j } = 0 . 4 \ , 0 . 3 2 \ , 0 . 1 6 \ , 0 . 1 2$ 时 $g _ { 3 } = 0 . 2 2 3 \mathrm { ~ } _ { , } g _ { 4 } = 0 . 1 4 5$ ，$\begin{array} { r } { g _ { 5 } = 0 . 1 2 5 ~ \ : g _ { 3 } = 0 . 0 9 7 } \end{array}$ 因此重要度排序为 $C R _ { 3 } { > } C R _ { 4 } { > } C R _ { 5 } { > } C R _ { 6 }$ ，即反映了在飞机 PHM 平台搭建时，应将实时故障监控、FMECA/FTA、故障隔离手册、诊断规则知识库整合到 1 个功能单元中，这 4 个功能相似度较高，具有互相支撑的作用，并且从客户需求的重要度可以看出，着重加强和提高实时故障监控子模块的功能，可以有效提升客户的满意度。相对地，航行信息与状态参数相似度较低，应建立独立的功能模块。

第2 步，搜集到的服务平台某个功能模块在当前时间节点以前的点击率、访客数、计算资源负荷、平均访问时长、流量占比等数据，通过 ARIMA 模型作出预测。本文通过对实时故障监控功能模块30 天的浏览量的统计，此外，利用SPSS对 ARIMA 模型中 $p$ ，d，q3 个参数取不同值进行模型对比［14］，表 2 列出其中3 个不同参数 ARIMA 模型的评价指标，以便选取最优的预测模型。

表 2 不同参数下 ARIMA 模型对比  

<html><body><table><tr><td>Model</td><td>ARIMA(2 11)</td><td>ARIMA(2 1 2)</td><td>ARIMA(1 2,1)</td></tr><tr><td>Stationary R²</td><td>0.079</td><td>0.026</td><td>0.295</td></tr><tr><td>R-square</td><td>0.141</td><td>0.092</td><td>0.015</td></tr><tr><td>RMSE</td><td>7662.976</td><td>8047.679</td><td>8330.762</td></tr><tr><td>MAPE</td><td>13.266</td><td>13.722</td><td>14.811</td></tr><tr><td>MAE</td><td>5241.246</td><td>5353.131</td><td>6119.302</td></tr><tr><td>Normalized BIC</td><td>18.469</td><td>18.683</td><td>18.531</td></tr></table></body></html>

根据方差( 最大) 、标准 BIC( 最小) 选择最适合的模型——ARIMA( 2，1，1) 预测之后 5 天的浏览量。

![](images/bdac397eba3b079e1e31056154a086e56900bf887ffdcef7644fb421283697aa.jpg)  
▲图3 服务平台30 天浏览量统计与 ARIMA 预测

通过观察实时故障监控功能模块 30 天的浏览量与 ARI-MA 预测可以直观得出未来 5 天需求有所下降，但总体维持平稳。如对点击率、访客数、计算资源负荷、平均访问时长、流量占比等数据做长期统计，利用上述 ARIMA 模型便可有效分析出各功能模块的客户需求的总体走势，填入下 1 步中服务资源向客户需求映射 HOQ 的计划矩阵中，增强服务资源匹配的动态响应能力。

表 3 浏览量( PV) 31 天－35 天的预测值  

<html><body><table><tr><td>模型ARIMA</td><td>日期</td><td>31</td><td>32</td><td>33</td><td>34</td><td>35</td></tr><tr><td rowspan="3">浏览量(PV)</td><td>预测</td><td>47 502</td><td>46520</td><td>45 523</td><td>44338</td><td>43 062</td></tr><tr><td>UCL</td><td>62 861</td><td>68 995</td><td>71 693</td><td>75 009</td><td>76 804</td></tr><tr><td>LCL</td><td>32 143</td><td>24 045</td><td>19 353</td><td>13 668</td><td>9321</td></tr></table></body></html>

第3 步，评估服务资源之间以及客户需求与服务资源之间的关联关系，并结合第 1 步基于的客户需求重要度排序以及第 2 步的需求预测结果填写服务资源向客户需求映射的HOQ。根据公式( 13) 计算当前服务匹配度为: 139、55、85、80、188、109、137、70。同理，根据计划矩阵的需求变化趋势得出服务匹配度预测，完成 HOQ。

![](images/6085694b6d03b41c179edae6c2713c874fe27d3ee880c16b701521408aa2c16b.jpg)  
▲图 4 客户需求与服务资源 QFD 匹配模型

服务匹配度决定了各项服务资源相对于客户需求的重要程度，评估了各项服务资源的价值高低; 匹配度预估表达了随着客户需求的动态变化各项服务资源相对于客户需求的价值变化。匹配度指标既能作为服务平台功能优势与不足的分析依据，又能评估服务资源相对重要性。

ARIMA 模型获取需求的动态特征，用于对 QFD 作下 1 步的调整改进，有助于服务资源调整、分配。将传统 QFD 应用到客户需求和服务资源的映射中，结合了灰色关联法和ARIMA 预测，更加真实准确地将客户需求数据化，同时增强了 QFD 的动态特性。有效地用工程语言将飞机 PLM 的服务资源与客户需求紧密结合，理清各种企业服务资源之间的关联和冲突情况，为服务平台搭建和改善提供可靠依据。

# 参考文献

［1］ 顾祝平，郑逢亮． 基于自动数据获得技术的飞机 CBM 维修策略［G］．2011 航空维修理论研究及技术发展学术交流会论文集，2011，8．  
［2］ HE L，SONG W，WU Z，et al． Quantification and integration of animproved Kano model into QFD based on multi－population adaptivegenetic algorithm［J］． Computers ＆ Industrial Engineering，2017，114: 183－194．  
［3］ KAHRAMAN C， ERTAY T， BYKZKAN G． A fuzzyoptimization model for QFD planning process using analytic networkapproach［J］． European Journal of Operational Research，2006，171( 2) : 390－411．  
［4］ SEBASTIAN R K，PERINPINAYAGAM S，CHOUDHARY R．Health management design considerations for an all electric aircraft［J］． Procedia CIRP，2017，59: 102－110．  
［5］ 李中凯，冯毅雄，谭建荣，等．基于灰色系统理论的质量屋中动态需求的分析与预测［J］．计算机集成制造系统，2009，15( 11) : 2272－2279．  
［6］ 王秋明，高慧颖，刘科成．基于模糊聚类及灰色关联的软件需求分析方法［J］．中国科学院研究生院学报，2010，27( 6) : 859－863．  
［7］ TANEJA K，AHMAD S，AHMAD K，et al． Time series analysis ofaerosol optical depth over new delhi using box － jenkins ARIMAmodeling approach［J］． Atmospheric Pollution Research，2016，7( 4) : 585－596．  
［8］ 王洵麟． 民用飞机航材管理信息系统分析与设计［D］． 上海: 上海交通大学，2014．  
［ 9 ］ ROSS R W． Integrated vehicle health management in aerospacestructures［M］．Structural Health Monitoring ( SHM) in AerospaceStructures，2016．  
［10］ 李朝玲，高齐圣． 在 QFD 中应用灰色关联度确定关联关系的研究［J］． 机械设计与研究，2008，24( 4) : 10－12．  
［11］ 侯智，张根保，余德忠，等． 基于 QFD，TRIZ 和稳健设计的设计方法体系结构研究［J］． 机械设计与研究，2003，19( 3) :17－19．  
［12］ 谢建中，杨育，张晓微，等．基于 FCM 和 IGA 的广义客户需求分析及其资源配置［J］．计算机集成制造系统，2015，21( 3) : 634－647．  
［13］ BABBAR C，AMIN S H． A multi － objective mathematical modelintegrating environmental concerns for supplier selection and orderallocation based on fuzzy QFD in beverages industry［J］． ExpertSystems with Applications，2018，92: 27－38．  
［14］ PUTRO S P，KOSHIO S，OKTAFERDIAN V． Implementation ofARIMA model to asses seasonal variability macrobenthicassemblages［J］． Aquatic Procedia，2016( 7) : 277－284．

# 6 结 论

本文针对民用飞机相关利益方复杂，全生命周期管理服务平台资源及业务众多的特点，提出飞机 PHM 平台的客户需求获取与推理研究框架。基于模糊理论对需求进行归类，划分功能模块。通过灰色关联法将利益相关方的需求进行重要度排序，作为 QFD 中客户需求权重的依据。基于