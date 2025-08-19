# 飞机开关磁阻发电系统故障推理模型研究

李宁，雷洪利，韩建定，朱喜华（空军工程大学工程学院，陕西西安710038）

摘要：开关磁阻发电系统是飞机供电系统的核心部分，为了研究飞机供电系统健康管理技术，减少故障推理模型的检测参数，满足飞机可靠性方面的要求，利用MATLAB软件对开关磁阻发电机典型电气故障进行了仿真分析，并引入记忆模块解决以往仿真过程中产生的代数环问题。然后将发电机输出电压信号利用EMD算法进行分解，将其分解后的各层频率信号的标准差作为特征量训练神经网络，得出开关磁阻发电系统的故障推理模型，本模型只需测量输出电压一个参数，减少了检测参数的数量，为开关磁阻发电系统故障预测模型及飞机整个供电系统健康管理系统的开发奠定了基础。

关键词：开关磁阻发电机；EMD；MATLAB/simulink；神经网络；故障中图分类号：TM31 文献标识码：A 文章编号：1002- 087X（2011）05- 0563- 04

# Fault deducing model research of switched reluctance power system of airplane based on PHM

LI Ning, LEI Hong- li, HAN Jian- ding, ZHU Xi- hua (Engineering College, Air- force Engineering University, Xi'an Shanxi 710038, China)

Abstract: The switched reluctance power system is the core of airplane power system. In order to research the application of PHM in the power system of airplane, reduce the measure parameters of the fault deducing model and satisfy the requirements of airplane dependability, the typical electric faults of SRG was carefully analyzed in this paper with MATLAB, and the memory module was used to solve the algebraic bop problem. The SRG voltage signal with EMD was analyzed, and the decomposed signal as character data was used to train the neural network and gain the fault concluding model of SRG main electrical power system. Only one parameter of the output voltage was needed to be measured with this model, which reduced the number of the measured parameters and was meaningful to the research of the prognostic model and PHM system of power system. Key words: switched reluctance generator; EMD; MATLAB/simulink; artificial neural network; fault

健康管理系统的应用为飞机供电系统的可靠性、维护的高效性、故障诊断及容错能力的提高提供了有力的保障，其中故障推理模型、故障预测模型的建立是健康管理系统的关键技术，但是检测参数过多是健康管理系统研究的一大课题。特别是航空领域，多参数测量所需的大量设备会降低系统的可靠性。

开关磁阻发电系统是一种新的飞机电源系统，它是伴随着多电飞机对电源系统性能所提出的更高要求而产生并迅速发展起来的一项新技术，具有发电容量大、效率高、起动和发电组合容易等优点[25]

本文对其典型电气故障进行了分析，借助MATLAB软件对其故障进行了仿真，为了减少特征参数的个数，选择开关磁阻发电机输出电压信号为特征信号，利用EMD算法对其按频率高低进行分解，利用分解后不同频率信号的标准差来

训练神经网络，最后建立开关磁阻发电系统的故障推理模型

# 1 开关磁阻发电系统的基本原理

本文研究的三相64结构的开关磁阻发电系统原理如图1所示，开关磁阻发电机发电过程分为励磁阶段和发电阶段，每相由两个IGBT作为开关器件，控制每相绕组的两个功率开关管导通，SRG处于励磁阶段；控制每相绕组的两个功率开关管均断，该相通过续流二极管释放能量，SRG处于发电阶段，发电机输出的电功率是发电阶段的发电功率与励磁阶段消耗功率之差[6]。

![](https://cdn-mineru.openxlab.org.cn/result/2025-07-19/8e2868be-89a5-4b0a-a99b-b85009428577/c8f6d1758e328c5d29dc5c202cbefdf93d8f32ad021603de88e149878aafe35c.jpg)  
图1 开关磁阻发电系统原理

# 2开关磁阻发电机故障及仿真分析

2 开关磁阻发电机故障及仿真分析主电源分系统是飞机整个供电系统的核心部分, 根据电源系统结构功能和测试性设计准则, 可将其分为开关磁阻发电机、功率变换器和发电机控制器三部分[7], 为了方便后文研究, 本文现对开关磁阻发电机的电气故障、故障编号确定如下: 定子绕组开路, 0001; 绕组短路, 0010; 绕组匝间短路, 0011; 绕组正端输出接地, 0100; 功率管开路, 0101; 功率管短路, 0110; 功率管输出接地, 0111; 正常状态的编号为 1000。

# 2.1开关磁阻发电机的仿真模型

# 2.1.1相电压方程式

若相绕组电流不为0，且电机工作在  $\partial L\partial \theta < 0$  ，电磁转矩为负，要使电机转动需外加正机械力矩，此时电机工作在发电状态，忽略功率器件饱和压降及相同互感，在发电模式下的相电压平衡方程式为[8]：

$$
u = R_{\mathrm{s}}i + L\frac{\mathrm{d}i}{\mathrm{d}t} +\frac{\mathrm{d}L}{\mathrm{d}g}\omega i \tag{1}
$$

式中：  $\pmb{u}$  为相绕组电压；  $R_{\mathrm{s}}$  为相绕组电阻；  $i$  为相绕组电流；  $L$  为该相绕组自感；  $\omega$  为转子的角速度。

# 2.1.2相绕组电感的模型

本文SRG的各项参数代码为：  $R$  为转子半径；  $D$  为转子轴长度；  $g$  为定转子凸极对齐时气隙长度；  $\alpha$  为每相绕组串联总匝数；  $\beta_{\mathrm{c}}$  为定子极弧；  $\beta_{\mathrm{s}}$  为转子极弧；  $\mu_{0}$  为气隙磁导率；  $\alpha$  为定子凸极和转子凸极对齐部分的弧度。

假设转子铁心的磁导率为无穷大，忽略漏磁通、边缘磁通和相间互感，相绕组的电感表示为[9]：

$$
L = \frac{N^{2}\mu_{0}\alpha R D}{2 g} \tag{2}
$$

根据图2的SRG相绕组电感线性模型，可得SRG的电感表达式为：

$$
L(\theta_{1})=\left\{\begin{array}{c c}{L_{\mathrm{min}}}&{\theta_{0}\leqslant\theta_{1}< \theta_{1}}\\ {K(\theta_{1}-\theta_{1})+L_{\mathrm{min}}}&{\theta_{1}\leqslant\theta_{1}< \theta_{2}}\\ {L_{\mathrm{max}}}&{\theta_{2}\leqslant\theta_{1}< \theta_{3}}\\ {L_{\mathrm{max}}-K(\theta_{1}-\theta_{3})}&{\theta_{3}\leqslant\theta_{1}< \theta_{4}}\\ {L_{\mathrm{min}}}&{\theta_{4}\leqslant\theta_{1}< \theta_{5}}\end{array}\right\} \tag{3}
$$

式中：  $k = (L_{\mathrm{max}} - L_{\mathrm{min}}) / \beta_{\mathrm{s}}$ $L_{\mathrm{max}} = N^{2}\mu_{0}\beta_{\mathrm{s}}R D / 2$ $\xi_{\mathrm{min}}$  为绕组电感的最大、最小值[10]

![](https://cdn-mineru.openxlab.org.cn/result/2025-07-19/8e2868be-89a5-4b0a-a99b-b85009428577/0d04162968a1586096b65d4bcfbcf50b8411cd3d2c3c40991d1ad3ac21f04d36.jpg)  
图2SRG相绕组电感线性模型

# 2.2仿真模型及结果分析

利用MATLAB/Simulink中的电力系统工具箱PSB搭建系统仿真模型如图3，主要仿真参数为：相电阻  $0.1\Omega$  ，导通角 $28^{\circ}$  ，关断角  $55^{\circ}$  ，转速  $7500~\mathrm{rad / s}$  ，负载电阻  $114\Omega$  ，输出电

![](https://cdn-mineru.openxlab.org.cn/result/2025-07-19/8e2868be-89a5-4b0a-a99b-b85009428577/a6faaf0b8c21ebc0303c8496cb922d979adb27b354a39883bd90d4f473b6b7c9.jpg)  
图3SRG仿真模型

容2F，PID参数，  $K_{\mathrm{p}} = 36$ $K_{\mathrm{r}} = 5$ $K_{\mathrm{d}} = 0$  ，转子极弧  $0.534\mathrm{rad}$  定子极弧0.581rad，单边气隙长度  $0.3\times 10^{- 3}\mathrm{m}$  ，仿真时间  $0.015\mathrm{s}$  方针算法ode23tb，其中绕组开路故障通过切除本相开关管的驱动信号来实现，故障设定时间为  $0.0095\mathrm{s}$  ，控制电路检测本相绕组电流值，当其超过额定值时，控制切除本相绕组，典型故障的仿真结果如图4、图5所示，由于本文故障推理模型以输出电压为特征量，所以仿真只给出典型故障下的电压图。另外针对仿真产生的代数环问题，文献[1]引入极点来消除代数环，本文在此基础上利用MATLAB/Simulink中的Memory模块很好地解决了这一问题。

![](https://cdn-mineru.openxlab.org.cn/result/2025-07-19/8e2868be-89a5-4b0a-a99b-b85009428577/f0fa2fe806bea53f13a832822927d95cdd443230bbdf5bde073b05cff8dda516.jpg)  
图4 功率管开路、短路电压

![](https://cdn-mineru.openxlab.org.cn/result/2025-07-19/8e2868be-89a5-4b0a-a99b-b85009428577/a982a04d7c544f91611e95c551248a4e5f4cdbbe2dcd2526602bcdec268639d2.jpg)  
图5绕组开路、接地故障电压

# 3基于EMD算法的开关磁阻发电机故障特征提取研究

# 3.1EMD算法的基本原理

NordenE.Huang 提出的经验模态分解（EmpiricalModeDecomposition，EMD)是一种新的自适应时频分析方法，它根据被分析信号的内在结构特征，将信号分解为若干个基本模式分量(IMF)，实现了信号自适应的频带划分，不同的基本模式分量包含有不同的故障信息。其经验模式分解原理如下：

（1）假设原始信号为  $x(t)$  ，用三次样条连接所有的局部极值点得到上下包络线，上下包络线的均值为  $m_{11}(t),x(t)$  与 $m_{11}(t)$  的差值定义为  $h_{11}(t)$  ，则

$$
h_{11}(t) = x(t) - m_{11}(t) \tag{4}
$$

(2）判断  $h_{11}(t)$  是否为基本模式分量，若  $h_{11}(t)$  不满足基本模式分量的两个条件，则将视为“新的原始信号”，重复以上步骤，直到满足两个条件为止。此时记  $c_{1}(t) = h_{11}(t)$  ，则  $c_{1}(t)$  为信号  $x(t)$  的第一个基本模式分量，它代表信号  $x(t)$  的最高频率分量。

（3）将  $c_{1}(t)$  从信号  $x(t)$  中分离出来，得到一个去掉高频分量的差信号，有：

$$
r_{1}(t) = x(t) - c_{1}(t) \tag{5}
$$

将  $r_{1}(t)$  视为新的原始时间序列，重复以上步骤，得到第二个基本模式分量  $c_{2}(t)$

（4）重复以上步骤，得到  $c_{3}(t),\dots ,c_{n}(t)$  ，此时  $x_{n}(t)$  变成一个

单调序列，其中不再包含任何模式的信息，这就是原始信号的余项  $r_{n}(t) = x_{n}(t)$

这样，原始信号  $x(t)$  被分解成个基本模式分量  $c_{1}(t)$  和一个余项残差  $r_{n}(t)$  之和，即有：

$$
x(t) = \sum_{n = 1}^{n}c_{1}(t) + r_{n}(t) \tag{6}
$$

# 3.2基于EMD算法的开关磁阻发电机特征提取

利用EMD算法对正常情况及典型故障下输出电压的仿真结果进行分解如图6，并以分解后每层信号的标准差为特征值如表1和表2，其中分解后频率最高层为第一层，依次到第八层。

![](https://cdn-mineru.openxlab.org.cn/result/2025-07-19/8e2868be-89a5-4b0a-a99b-b85009428577/6b16c0cdb19384412dd51071520551e0ea58de755d331a0a8267a3bd741d7b2c.jpg)  
图6（1） 正常情况

![](https://cdn-mineru.openxlab.org.cn/result/2025-07-19/8e2868be-89a5-4b0a-a99b-b85009428577/f4e3200dae31a119a8df4ac3d5c1136a3c16eecdf34740278035d89970f39eb4.jpg)  
图6（2）绕组短路

![](https://cdn-mineru.openxlab.org.cn/result/2025-07-19/8e2868be-89a5-4b0a-a99b-b85009428577/fbf83490bee9f9a1f9458dc8c35730dbdeccbf40e330b1e2e9c06e17043a6f5d.jpg)  
图6（3） 功率管开路

表1  $0.009\sim 0.012s$  信号分解后的标准差  

<table><tr><td>标准差</td><td>第1层</td><td>第2层</td><td>第3层</td><td>第4层</td><td>第5层</td><td>第6层</td><td>第7层</td><td>第8层</td></tr><tr><td>正常状态</td><td>0.0403</td><td>0.0631</td><td>0.0683</td><td>0.0615</td><td>0.0877</td><td>0.0550</td><td>0.0281</td><td>0.0719</td></tr><tr><td>绕组开路</td><td>0.0364</td><td>0.0587</td><td>0.0600</td><td>0.0699</td><td>0.0991</td><td>0.1164</td><td>0.1198</td><td>0.1341</td></tr><tr><td>绕组短路</td><td>0.0702</td><td>0.0359</td><td>0.0628</td><td>0.0495</td><td>0.0495</td><td>0.0563</td><td>0.0298</td><td>0.1126</td></tr><tr><td>匝间短路</td><td>0.0367</td><td>0.0639</td><td>0.0658</td><td>0.0615</td><td>0.0917</td><td>0.0868</td><td>0.0336</td><td>0.0799</td></tr><tr><td>绕组接地</td><td>0.4856</td><td>0.4332</td><td>0.2963</td><td>1.9893</td><td>1.9934</td><td>1.9832</td><td>1.9145</td><td>0.4861</td></tr><tr><td>功率管开路</td><td>0.0491</td><td>0.0749</td><td>0.0779</td><td>0.0800</td><td>0.0889</td><td>0.0683</td><td>0.0421</td><td>0.1656</td></tr><tr><td>功率管短路</td><td>0.0387</td><td>0.0571</td><td>0.0853</td><td>0.0992</td><td>0.0826</td><td>0.0494</td><td>0.0168</td><td>0.0859</td></tr><tr><td>功率管输出接地</td><td>0.0335</td><td>0.0568</td><td>0.0828</td><td>0.0822</td><td>0.0928</td><td>0.0542</td><td>0.0212</td><td>0.1201</td></tr></table>

表2  $0.012\sim 0.015s$  信号分解后的标准差  

<table><tr><td>标准差</td><td>第1层</td><td>第2层</td><td>第3层</td><td>第4层</td><td>第5层</td><td>第6层</td><td>第7层</td><td>第8层</td></tr><tr><td>正常状态</td><td>0.0418</td><td>0.0628</td><td>0.0719</td><td>0.0624</td><td>0.0873</td><td>0.0544</td><td>0.0219</td><td>0.0735</td></tr><tr><td>绕组开路</td><td>0.0381</td><td>0.0566</td><td>0.0624</td><td>0.0730</td><td>0.0973</td><td>0.1206</td><td>0.1176</td><td>0.1385</td></tr><tr><td>绕组短路</td><td>0.0743</td><td>0.0388</td><td>0.0603</td><td>0.0517</td><td>0.0469</td><td>0.0582</td><td>0.0324</td><td>0.0926</td></tr><tr><td>匝间短路</td><td>0.0383</td><td>0.0627</td><td>0.0714</td><td>0.0586</td><td>0.0891</td><td>0.0842</td><td>0.0397</td><td>0.0827</td></tr><tr><td>绕组接地</td><td>0.4864</td><td>0.4379</td><td>0.2938</td><td>1.9905</td><td>1.9908</td><td>1.9854</td><td>1.9121</td><td>0.4899</td></tr><tr><td>功率管开路</td><td>0.0418</td><td>0.0761</td><td>0.0811</td><td>0.0856</td><td>0.0956</td><td>0.0704</td><td>0.0398</td><td>0.1708</td></tr><tr><td>功率管短路</td><td>0.0403</td><td>0.0532</td><td>0.0802</td><td>0.0957</td><td>0.0886</td><td>0.0536</td><td>0.0197</td><td>0.0837</td></tr><tr><td>功率管输出接地</td><td>0.0368</td><td>0.0589</td><td>0.0869</td><td>0.0873</td><td>0.0891</td><td>0.0509</td><td>0.0178</td><td>0.1181</td></tr></table>

# 4基于B-P神经网络的故障推理模型研究

利用表1和表2的两组数据作为特征量分别训练、验证神经网络，根据信号分解后的层数及故障的编号，选择神经网

络的输入层8，输出层为4，隐含层分别取6、8、10、12、15、20，可得当隐含层取10时收敛步数最小为166，选择输入层函数、传递函数及输出层函数均为tansig，可得最小收敛步数118，验证结果如表3。

表3 神经网络验证结果  

<table><tr><td colspan="4">实际输出</td><td colspan="3">期望输出</td></tr><tr><td>0.751 360</td><td>0.551 55</td><td>0.553 040</td><td>-0.196 960</td><td>1</td><td>0</td><td>0</td></tr><tr><td>-0.011 667</td><td>0.105 03</td><td>0.068 9550</td><td>0.998 700</td><td>0</td><td>0</td><td>0</td></tr><tr><td>-0.108 960</td><td>-0.138 96</td><td>0.979 350</td><td>-0.385 590</td><td>0</td><td>0</td><td>1</td></tr><tr><td>-0.176 320</td><td>0.317 94</td><td>0.768 460</td><td>0.860 350</td><td>0</td><td>0</td><td>1</td></tr><tr><td>-0.019 718</td><td>1.000 00</td><td>0.048 876</td><td>-0.118 560</td><td>0</td><td>1</td><td>0</td></tr><tr><td>0.112 010</td><td>0.999 14</td><td>0.002 977 7</td><td>0.998 750</td><td>0</td><td>1</td><td>0</td></tr><tr><td>0.063 632</td><td>0.956 33</td><td>0.901 650</td><td>-0.008 509 2</td><td>0</td><td>1</td><td>1</td></tr><tr><td>-0.084 209</td><td>0.995 03</td><td>0.813 550</td><td>0.873 680</td><td>0</td><td>1</td><td>1</td></tr></table>

# 5结论

作为新的飞机电源系统，开关磁阻发电系统具有发电容量大、效率高，起动和发电组合容易等优点，具有很大的应用前景，本文通过对其典型电气故障进行详细分析，并借助MATLAB软件对其故障进行仿真，以开关磁阻发电机输出电压信号为特征信号，利用EMD算法对其按频率高低进行分解，利用分解后不同频率信号的标准差来训练神经网络，最后建立开关磁阻发电机主电源系统的故障推理模型，减少了故障诊断的检测参数，为健康管理系统在飞机供电系统中的应用奠定了基础。

# 参考文献：

[1]巩建英，刘卫国.开关磁阻发电系统仿真与稳定性分析[J].系统仿真学报，2009，21(20)：6634- 6638. [2]方天治，赵德安.开关磁阻发电机的控制模式及仿真研究[J].计

算机仿真，2004，21（4）：51- 53.

[3]刘震，林辉，司利云.开关磁阻发电系统故障分析与仿真[J].电力系统及其自动化学报，2005，17（5）：7- 11. [4]刘震，林辉，徐敏.多电飞机开关磁阻发电系统的数字仿真研究[J].系统仿真学报，2005，17（12）：3070- 3073. [5]张慧.开关磁阻发电机系统的研究[D].浙江：浙江大学，2003. [6]陈东锁.开关磁阻电机驱动系统的动态模型及仿真[D].太原：太原理工大学，2002. [7]顾明磊.开关磁阻电机发电控制系统的研究[D].武汉：华中科技大学，2007. [8]张慧.开关磁阻发电机系统的研究[D].杭州：浙江大学，2003. [9]FAIZ J, MOAYED- ZADEH K. Design of switched reluctance machine for starter/generator of hybrid electric vehicle [J]. Electric Power Systems Research (S0378- 7796), 2005, 75(2): 153- 160. [10]ZHANG J H, ARTHUR V R. A new method to measure the switched reluctance motor's flux [J]. IEEE Transaction on Industry Applications (S0093- 9594), 2006, 42(5): 1171- 1176.