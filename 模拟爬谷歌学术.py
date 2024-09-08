import re
from time import sleep
from urllib import parse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service

from databaseUtil import *
from printUtil import *


def parse_gb7714_citation(citation):
    # 定义正则表达式模式以匹配文章标题、期刊名称和发表年份
    pattern = r'^(.*?)\. (.*?)\[(.*?)\]\. (.*?)\, (\d{4})'

    match = re.match(pattern, citation)
    if match:
        # 提取匹配到的内容
        authors = match.group(1).strip()
        title = match.group(2).strip()
        journal_info = match.group(3).strip()
        journal_name = match.group(4).strip()
        year = match.group(5).strip()

        return {
            'title': title,
            'journal_name': journal_name,
            'year': year
        }
    else:
        return None



class GetBibs():
    def __init__(self, gg_search_url,chrome_driver_path) -> None:
        # 当前检索的文章标题
        self.title = ''
        # 谷歌学术地址
        self.gg_search_url = gg_search_url
        # 创建 WebDriver 实例
        self.browser = webdriver.Chrome(service=Service(executable_path=chrome_driver_path), options=webdriver.ChromeOptions())


    def deal_captcha(self):
        # 判断是是否为验证码页
        while len(self.browser.find_elements(By.ID, 'gs_captcha_ccl')) != 0:
            print_red("检测到验证码，请手动处理完后，再按回车继续")
            input()


    # 进入被引用文献链接
    def get_title_to_google_scholar(self, paper_title):
        # 记录本次爬的文章标题
        self.title = paper_title

        # 拼接论文搜索url，并访问
        url = self.gg_search_url + parse.quote(paper_title)
        self.browser.get(url)

        # 定位到搜索结果页查询到的论文列表
        links = (self.browser
                 .find_element(By.CSS_SELECTOR, "[class='gs_r gs_or gs_scl gs_fmar']")
                 .find_element(By.CSS_SELECTOR, "[class='gs_fl gs_flb']")
                 .find_elements(By.XPATH, "a"))

        # todo： 如果搜索到的论文数量超过1，报错

        # 点击目标论文的 “被引用次数”按钮
        element = links[2]
        element.click()
        # 处理验证码
        self.deal_captcha()

        # 解析引用的文章
        self.get_data_from_google_scholar()

    def get_data_from_google_scholar(self):
        old_url = self.browser.current_url
        page_count = 0
        while True:
            try:
                # 处理第page_count 的引用文章搜索结果
                has_more_data = self.deal_with_page(page_count,old_url)
                if not has_more_data:
                    # 当前页没有数据了，结束搜索
                    break
                page_count = page_count+1
            except Exception as e:
                print_red("刷新页面，处理机器人验证后按回车")
                input()


    def deal_with_page(self,page_count,old_url):
        # 拼接第page_count页的引用论文的搜索页url
        url = old_url.split('scholar?')[0] + 'scholar?start=' + str(10 * page_count) + '&' + old_url.split('scholar?')[1]

        # 跳转搜索结果页，并处理验证码
        self.browser.get(url)
        self.deal_captcha()

        # 当前页面的10篇文章
        query_cited_result = self.browser.find_elements(By.CSS_SELECTOR, "[class='gs_r gs_or gs_scl']")
        if len(query_cited_result) == 0:
            # 没有更多数据了
            return False

        for i in range(len(query_cited_result)):
            # 解析当前页的第i个论文
            i_paper = self.browser.find_elements(By.CSS_SELECTOR, "[class='gs_r gs_or gs_scl']")[i]


            # 等待论文底栏加载完成,定位底栏的 “引用”按钮
            WebDriverWait(self.browser, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "[class='gs_fl gs_flb']"))
            )
            items = []
            while len(items) == 0:
                items = (i_paper
                         .find_element(By.CSS_SELECTOR, "[class='gs_fl gs_flb']")
                         .find_elements(By.XPATH, "a"))
            quote_button = items[1]

            # 等待“引用”按钮可点击之后，点击该按钮
            WebDriverWait(self.browser, 10).until(EC.element_to_be_clickable(quote_button))
            sleep(2)
            quote_button.click()
            sleep(3)

            # 等待引用页加载完成
            WebDriverWait(self.browser, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "[class='gs_citr']"))
            )

            # 定位到gb774的引用内容
            citrs = []
            while len(citrs) == 0:
                citrs = self.browser.find_elements(By.CSS_SELECTOR, "[class='gs_citr']")
            gb774_cit = citrs[0].text

            # 解析引用格式
            result = parse_gb7714_citation(gb774_cit)
            if result:
                save_if_absent(self.title, gb774_cit, result['title'], result['journal_name'], result['year'])
            else:
                print_red(f"Failed to parse the citation.{gb774_cit}")
                save_if_absent(self.title, gb774_cit, '', '', '')

            # 点击关闭引用的x
            WebDriverWait(self.browser, 10).until(
                EC.element_to_be_clickable((By.ID, 'gs_cit-x'))
            )
            self.browser.find_element(By.ID, "gs_cit-x").click()

        return True

if __name__ == '__main__':
    # 替换为本机实际 chromedriver 路径
    # chrome_driver_path = "/Users/liuchang/PycharmProjects/LPTHW/chromedriver-mac-arm64/chromedriver"

    chrome_driver_path = "/Users/bytedance/Downloads/生成式/字帖/chromedriver-mac-arm64/chromedriver"
    gg_search_url = r'https://scholar.google.com/scholar?hl=zh-CN&as_sdt=0%2C5&inst=1597255436240989024&q='

    # 创建爬虫对象
    get_bibs = GetBibs(gg_search_url,chrome_driver_path)

    # 要爬取的文章标题
    paper_titles = [
                    # 'Multiwavelength high-order optical vortex detection and demultiplexing coding using a metasurface',
                    #'Deep learning spatial phase unwrapping: a comparative review',
                    # 'General treatment of dielectric perturbations in optical rings',
                    # 'Orbital angular momentum comb generation from azimuthal binary phases',
                    # 'Deterministic generation of large-scale hyperentanglement in three degrees of freedom',
                    # 'Ultra-broadband and low-loss edge coupler for highly efficient second harmonic generation in thin-film lithium niobate',
                    # 'Light-induced vacuum micromotors based on an antimony telluride microplate',
                    # 'Nanochannels with a 18-nm feature size and ultrahigh aspect ratio on silica through surface assisting material ejection',


                    # 'Recent advances in photonics of three-dimensional Dirac semimetal',
                    # 'Janus vortex beams realized via liquid crystal Pancharatnam–Berry phase elements',
                    # 'Centimeter scale color printing with grayscale lithography',
                    # 'Deep-tissue two-photon microscopy with a frequency-doubled all-fiber mode-locked laser at 937 nm',
                    # 'Ultracompact phase plate fabricated by femtosecond laser two-photon polymerization for generation of Mathieu--Gauss beams',
                    # 'Hybrid reconstruction of the physical model with the deep learning that improves structured illumination microscopy',
                    # 'Deep-learning-assisted inverse design of dual-spin/frequency metasurface for quad-channel off-axis vortices multiplexing',
                    # 'Confocal rescan structured illumination microscopy for real-time deep tissue imaging with superresolution',
                    # 'Detection of trace metals in water by filament- and plasma-grating-induced breakdown spectroscopy',
                    # 'Characterization of multimode linear optical networks',
                    # 'Optical reflective metasurfaces based on mirror-coupled slot antennas',
                    # 'On-chip tunable parity‐time symmetric optoelectronic oscillator',
                    # 'Vortex-induced quasi-shear polaritons',
                    # 'Anomalous broadband Floquet topological metasurface with pure site rings',
                    # 'Deterministic <i>N</i>-photon state generation using lithium niobate on insulator device',
                    # 'Ultrafast optical phase-sensitive ultrasonic detection via dual-comb multiheterodyne interferometry',
                    # 'Laterally swept light-sheet microscopy enhanced by pixel reassignment for photon-efficient volumetric imaging',
                    # 'Toward augmenting tip-enhanced nanoscopy with optically resolved scanning probe tips',
                    # 'Supporting quantum technologies with an ultralow-loss silicon photonics platform',
                    # 'Noncontact photoacoustic lipid imaging by remote sensing on first overtone of the C-H bond',
                    # 'Scattered light imaging beyond the memory effect using the dynamic properties of thick turbid media',
                    # 'Reflective optical vortex generators with ultrabroadband self-phase compensation',
                    # 'High-speed hyperspectral imaging enabled by compressed sensing in time domain',
                    # 'Controllable valley magnetic response in phase-transformed tungsten diselenide',
                    # 'Nondiffractive three-dimensional polarization features of optical vortex beams',
                    # 'Relative phase locking of a terahertz laser system configured with a frequency comb and a single-mode laser',
                    # 'Realization of advanced passive silicon photonic devices with subwavelength grating structures developed by efficient inverse design',
                    # 'Large-scale single-crystal blue phase through holography lithography',
                    # 'Evolution on spatial patterns of structured laser beams: from spontaneous organization to multiple transformations',
                    # 'Real-time monitoring of polarization state deviations with dielectric metasurfaces',
                    # 'Self-seeded free-electron lasers with orbital angular momentum',
                    # 'Fringe-pattern analysis with ensemble deep learning',
                    # 'Deep image prior plus sparsity prior: toward single-shot full-Stokes spectropolarimetric imaging with a multiple-order retarder',
                    # 'Direct laser-written aperiodic photonic volume elements for complex light shaping with high efficiency: inverse design and fabrication',
                    # 'Structural designs of AlGaN/GaN nanowire-based photoelectrochemical photodetectors: carrier transport regulation in GaN segment as current flow hub',
                    # 'Generation of high-efficiency, high-purity, and broadband Laguerre-Gaussian modes from a Janus optical parametric oscillator',
                    # 'Reconfigurable structured light generation and its coupling to air–core fiber',
                    # 'Low-insertion-loss femtosecond laser-inscribed three-dimensional high-density mux/demux devices',
                    # 'High-repetition-rate seeded free-electron laser enhanced by self-modulation',
                    # 'Long-range chaotic Brillouin optical correlation domain analysis with more than one million resolving points',
                    # 'Statistical dynamics of noise-like rectangle pulse fiber laser',
                    # 'Characteristics of a Gaussian focus embedded within spiral patterns in common-path interferometry with phase apertures',
                    # 'Joint device architecture algorithm codesign of the photonic neural processing unit',
                    # 'Multiparameter encrypted orbital angular momentum multiplexed holography based on multiramp helicoconical beams',
                    # 'Multifunctional interface between integrated photonics and free space',
                    # 'Complex-domain-enhancing neural network for large-scale coherent imaging',
                    # 'Complete active–passive photonic integration based on GaN-on-silicon platform',
                    # 'Printable organic light-emitting diodes for next-generation visible light communications: a review',
                    # 'Review on near-field detection technology in the biomedical field',
                    # 'Photoacoustic-enabled automatic vascular navigation: accurate and naked-eye real-time visualization of deep-seated vessels',
                    # 'Generation and control of extreme ultraviolet free-space optical skyrmions with high harmonic generation',
                    # 'Experimental optical computing of complex vector convolution with twisted light',
                    # 'Untrained neural network enhances the resolution of structured illumination microscopy under strong background and noise levels',
                    # 'Compact microring resonator based on ultralow-loss multimode silicon nitride waveguide',
                    # 'Thermal camera based on frequency upconversion and its noise-equivalent temperature difference characterization',
                    # 'Digital subcarrier multiplexing-enabled carrier-free phase-retrieval receiver',
                    # 'Recent advances in deep-learning-enhanced photoacoustic imaging',
                    # 'Achieving higher photoabsorption than group III-V semiconductors in ultrafast thin silicon photodetectors with integrated photon-trapping surface structures',
                    # 'Differentiated design strategies toward broadband achromatic and polarization-insensitive metalenses',
                    # 'Achromatic on-chip focusing of graphene plasmons for spatial inversions of broadband digital optical signals',
                    # 'Operation of multiphonon-assisted laser in the nanosecond time scales',
                    # 'Generation of biaxially accelerating static Airy light-sheets with 3D-printed freeform micro-optics',
                    # 'Highly sensitive miniature needle PVDF-TrFE ultrasound sensor for optoacoustic microscopy',
                    # 'Efficient reference-less transmission matrix retrieval for a multimode fiber using fast Fourier transform',
                    # 'High-fidelity SIM reconstruction-based super-resolution quantitative FRET imaging',
                    # 'High repetition rate ultrafast laser-structured nickel electrocatalyst for efficient hydrogen evolution reaction',
                    # 'High-speed free-space optical communication using standard fiber communication components without optical amplification',
                    # 'Robust moiré flatbands within a broad band-offset range',
                    # 'Miniaturized short-wavelength infrared spectrometer for diffuse light applications',
                    # 'Coordination engineering in Nd doped silica glass for improving repetition rate of 920-nm ultrashort-pulse fiber laser',
                    # 'Nonconvex optimization for optimum retrieval of the transmission matrix of a multimode fiber',
                    # 'High-quality-factor space–time metasurface for free-space power isolation at near-infrared regime',
                    # 'Reconfigurable optical add-drop multiplexers for hybrid mode-/wavelength-division-multiplexing systems',
                    # 'Advanced all-optical classification using orbital-angular-momentum-encoded diffractive networks',
                    # 'Dissipative soliton breathing dynamics driven by desynchronization of orthogonal polarization states',
                    # 'Coherently tiled Ti:sapphire laser amplification: a way to break the 10 petawatt limit on current ultraintense lasers',
                    # 'Electromagnetic modeling of interference, confocal, and focus variation microscopy',
                    # 'Terahertz probe for real time <i>in vivo</i> skin hydration evaluation',
                    # 'Dual-channel quantum meta-hologram for display',
                    # 'Complex-valued universal linear transformations and image encryption using spatially incoherent diffractive networks',
                    # 'Experimental observation of topological large-area pseudo-spin-momentum-locking waveguide states with exceptional robustness',
                    # 'Intense white laser of high spectral flatness via optical-damage-free water–lithium niobate module',
                    # 'Carbon-based ultrabroadband tunable terahertz metasurface absorber',
                    # 'Ultra-low-loss all-fiber orbital angular momentum mode-division multiplexer based on cascaded fused-biconical mode selective couplers',
                    # 'Multidimensional multiplexing holography based on optical orbital angular momentum lattice multiplexing',
                    # 'High-speed autopolarization synchronization modulation three-dimensional structured illumination microscopy',
                    # 'Secure optical interconnects using orbital angular momentum beams multiplexing/multicasting',
                    # '100 Gb/s coherent chaotic optical communication over 800 km fiber transmission via advanced digital signal processing',
                    # 'Spectrum shuttle for producing spatially shapable GHz burst pulses',
                    # 'High-power, narrow linewidth solid-state deep ultraviolet laser generation at 193 nm by frequency mixing in LBO crystals',
                    # 'Nonuniform pseudo-magnetic fields in photonic crystals',
                    # 'Physics-constrained deep-inverse point spread function model: toward non-line-of-sight imaging reconstruction',
                    # 'Multiparameter performance monitoring of pulse amplitude modulation channels using convolutional neural networks',
                    # 'Unveiling optical rogue wave behavior with temporally localized structures in Brillouin random fiber laser comb',
                    # 'Multimode diffractive optical neural network',
                    # 'High spatial resolution collinear chiral sum-frequency generation microscopy',
                    # 'Retrieving  Jones matrix from an imperfect metasurface polarizer',
                    # '635 nm femtosecond fiber laser oscillator and amplifier',
                    # 'Generation of subwavelength inverted pin beam via fiber end integrated plasma structure',
                    # 'Spectral transfer-learning-based metasurface design assisted by complex-valued deep neural network',
                    # 'Azimuthal beam shaping in orbital angular momentum basis',
                    # 'Generation of tunable high-order Laguerre–Gaussian petal-like modes from a mid-infrared optical vortex parametric oscillator',
                    # 'High-performance silicon arrayed-waveguide grating (de)multiplexer with 0.4-nm channel spacing',
                    # 'Photonic implementation of quantum gravity simulator Cover',
                    # 'Simultaneous sorting of arbitrary vector structured beams with spin-multiplexed diffractive metasurfaces',
                    # 'Random fiber laser using a cascaded fiber loop mirror',
                    # 'Suppressing neuroinflammation using the near-infrared light emitted by (Sr,Ba)Ga<sub>12</sub>O<sub>19</sub>: Cr<sup>3+</sup> phosphor',
                    # 'Beyond 200-Gb/s O-band intensity modulation and direct detection optics with joint look-up-table-based predistortion and digital resolution enhancement for low-cost data center interconnects',
                    # 'Nonlinear localization of ultracold atomic Fermi gas in moiré optical lattices',
                    # 'PC-bzip2: a phase-space continuity-enhanced lossless compression algorithm for light-field microscopy data',
                    # 'Frequency-dependent selectively oriented edge state topological transport',
                    # 'Integrated coherent beam combining system for orbital-angular-momentum shift-keying-based free-space optical links',
                    # 'Single-wavelength size focusing of ultra-intense ultrashort lasers with rotational hyperbolic mirrors',
                    # 'Split Lohmann computer holography: fast generation of 3D hologram in single-step diffraction calculation',
                    # 'Enhanced terahertz generation via plasma modulation on two bunches',
                    # 'Hybrid optical parametrically oscillating emitter-enabled photoacoustic imaging of water: enhanced contrast, dynamic range, and multifaceted applications',


                    'Stable high-peak-power fiber supercontinuum generation for adaptive femtosecond biophotonics',
                    'Temperature-insensitive fiber-optic refractive index sensor based on cascaded in-line interferometer and microwave photonics interrogation system',
                    'Multimode fiber speckle Stokes polarimeter',
                    'Robust spectral reconstruction algorithm enables quantum dot spectrometers with subnanometer spectral accuracy',
                    'Achieving high-security and massive-capacity optical communications based on orbital angular momentum configured chaotic laser',
                    'Extremely efficient terahertz second-harmonic generation from organic crystals',
                    'Rapid and precise distance measurement with hybrid comb lasers',
                    'Self-mode-locking optoelectronic oscillator with ultrashort time delay',
                    'Manipulable multipurpose nanothermometers based on a fluorescent hybrid glass fiber microsphere cavity',
                    'Decision-making and control with diffractive optical networks',
                    'Highly sensitive mid-infrared upconversion detection based on external-cavity pump enhancement',
                    'Flexible depth-of-focus, depth-invariant resolution photoacoustic microscopy with Airy beam',
                    'Silicon thermo-optic phase shifters: a review of configurations and optimization strategies'
                    ]  # 要爬取的论文，key用于标记，value是论文题目。下面是一些样例

    for title in paper_titles:
        print_yellow(f"----------start({title})-------------")
        get_bibs.get_title_to_google_scholar(title)
        print_green(f"----------end({title})-------------")
