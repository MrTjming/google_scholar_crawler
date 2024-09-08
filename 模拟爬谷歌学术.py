from time import sleep
from urllib import parse
from selenium import webdriver
from selenium.webdriver.common.by import By
from colorama import Fore, Style,init
from peewee import *
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 初始化 colorama
init(autoreset=True)

def print_header(text):
    print(Fore.MAGENTA + text)

def print_blue(text):
    print(Fore.BLUE + text)

def print_cyan(text):
    print(Fore.CYAN + text)

def print_green(text):
    print(Fore.GREEN + text)

def print_yellow(text):
    print(Fore.YELLOW + text)

def print_red(text):
    print(Fore.RED + text)

def print_bold(text):
    print(Style.BRIGHT + text)



# 连接到 SQLite 数据库
db = SqliteDatabase('论文引用数据库.db')

# 定义模型类
class QuoteInfo(Model):
    #
    title = CharField(max_length=500)
    citationGBT = CharField(max_length=500)
    # 引用的文章名
    cited_by_title = CharField(max_length=500)
    journal= CharField(max_length=500)
    year_month= CharField(max_length=20)

    class Meta:
        database = db  # 使用数据库连接
        table_name = 'quoteInfo' + '20240908'

# 创建表
db.connect()
db.create_tables([QuoteInfo])

def save_if_absent(title, citationGBT, cited_by_title, journal,year_month):
    users = QuoteInfo.select().where((QuoteInfo.title == title) & (QuoteInfo.citationGBT == citationGBT))
    if len(users) == 0:
        QuoteInfo.create(title=title,citationGBT=citationGBT, cited_by_title=cited_by_title,journal=journal, year_month=year_month)


import re


import re

import re


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


from selenium.webdriver.chrome.service import Service

class GetBibs():
    def __init__(self, gg_search_url) -> None:
        self.gg_search_url = gg_search_url
        # 启用带插件的浏览器

        chrome_driver_path = "/Users/liuchang/PycharmProjects/LPTHW/chromedriver-mac-arm64/chromedriver"  # 替换为实际 chromedriver 路径
        service = Service(executable_path=chrome_driver_path)

        options = webdriver.ChromeOptions()

        # 创建 WebDriver 实例
        self.browser = webdriver.Chrome(service=service, options=options)
        self.title = ''

    def deal_captcha(self):
        # 判断是验证码
        while self.check_captcha():
            print_red("检测到验证码，请手动处理完后，再按回车继续")
            input()

    def check_captcha(self) -> bool:
        """检查是否需要人机验证；一个是谷歌学术的、一个是谷歌搜索的"""
        return self.check_element_exist_by_id( value='gs_captcha_ccl')

    def check_element_exist_by_id(self ,value):
        res = self.browser.find_elements(By.ID, value)
        if len(res) == 0:
            return False
        return True

    # 进入被引用文献链接
    def get_title_to_google_scholar(self, paper_title):
        self.title = paper_title
        url = self.gg_search_url + parse.quote(paper_title)
        self.browser.get(url)
        # 等待词条加载,得到数据
        for i in range(100):
            try:
                links = self.browser.find_element(By.CSS_SELECTOR, "[class='gs_r gs_or gs_scl gs_fmar']").find_element(
                    By.CSS_SELECTOR, "[class='gs_fl gs_flb']").find_elements(By.XPATH, "a")
                # print(links[2].get_attribute('href'))
                element = links[2]
                element.click()
                self.deal_captcha()
                break
            except:
                sleep(0.1)

        self.get_data_from_google_scholar()
    def deal_with_page(self,page_count,old_url):
        url_head = old_url.split('scholar?')[0]
        url_tail = old_url.split('scholar?')[1]
        url = url_head + 'scholar?start=' + str(10 * page_count) + '&' + url_tail
        self.browser.get(url)
        self.deal_captcha()
        # print(f"count is {page_count},url is {self.browser.current_url},title is {self.browser.title}")
        # 当前页面的10篇文章
        elements = self.browser.find_elements(By.CSS_SELECTOR, "[class='gs_r gs_or gs_scl']")
        if len(elements) == 0:
            return False
        for i in range(len(elements)):
            element = self.browser.find_elements(By.CSS_SELECTOR, "[class='gs_r gs_or gs_scl']")[i]
            # try:
            items = []
            WebDriverWait(self.browser, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "[class='gs_fl gs_flb']"))
            )
            while len(items) == 0:
                items = element.find_element(By.CSS_SELECTOR, "[class='gs_fl gs_flb']").find_elements(By.XPATH, "a")
            WebDriverWait(self.browser, 10).until(EC.element_to_be_clickable(items[1]))
            sleep(2)
            items[1].click()
            sleep(3)
            citrs = []
            WebDriverWait(self.browser, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "[class='gs_citr']"))
            )
            while len(citrs) == 0:
                citrs = self.browser.find_elements(By.CSS_SELECTOR, "[class='gs_citr']")

            cit = citrs[0].text
            # print(cit)

            result = parse_gb7714_citation(cit)

            if result:
                save_if_absent(self.title, cit, result['title'], result['journal_name'], result['year'])
            else:
                print_red(f"Failed to parse the citation.{cit}")
                save_if_absent(self.title, cit, '', '', '')
                # print(cit)
            # 关闭引用框框
            element = WebDriverWait(self.browser, 10).until(
                EC.element_to_be_clickable((By.ID, 'gs_cit-x'))
            )
            self.browser.find_element(By.ID, "gs_cit-x").click()
        sleep(1)
        return True
    def get_data_from_google_scholar(self):
        old_url = self.browser.current_url
        page_count = 0
        while True:
            try:
                succeed = self.deal_with_page(page_count,old_url)
                if not succeed:
                    break
                page_count = page_count+1
            except Exception as e:
                print_red("刷新页面，处理机器人验证后按回车")
                input()



# option_path = r"C:/Users/Administrator/AppData/Local/Google/Chrome/User Data - 副本/"  # 使浏览器能用你自定义的设置，否则Selenium创建的浏览器对象是默认设置，一些插件就不能用了
gg_search_url = r'https://scholar.google.com/scholar?hl=zh-CN&as_sdt=0%2C5&inst=1597255436240989024&q='  # 在执行代码之前，先打开搜索页面，把类似的网址复制到这里，等号=后面就是一会儿要搜索的内容
get_bibs = GetBibs(gg_search_url)


# %% **********************以上定义爬虫对象，以下开始爬取*******************************

paper_titles = [
                # 'Multiwavelength high-order optical vortex detection and demultiplexing coding using a metasurface',
                #'Deep learning spatial phase unwrapping: a comparative review',
                # 'General treatment of dielectric perturbations in optical rings',
                # 'Orbital angular momentum comb generation from azimuthal binary phases',
                # 'Deterministic generation of large-scale hyperentanglement in three degrees of freedom',
                # 'Ultra-broadband and low-loss edge coupler for highly efficient second harmonic generation in thin-film lithium niobate',
                # 'Light-induced vacuum micromotors based on an antimony telluride microplate',
                # 'Nanochannels with a 18-nm feature size and ultrahigh aspect ratio on silica through surface assisting material ejection',
                'Recent advances in photonics of three-dimensional Dirac semimetal',
                'Janus vortex beams realized via liquid crystal Pancharatnam–Berry phase elements',
                'Centimeter scale color printing with grayscale lithography',
                'Deep-tissue two-photon microscopy with a frequency-doubled all-fiber mode-locked laser at 937 nm',
                'Ultracompact phase plate fabricated by femtosecond laser two-photon polymerization for generation of Mathieu--Gauss beams',
                'Hybrid reconstruction of the physical model with the deep learning that improves structured illumination microscopy',
                'Deep-learning-assisted inverse design of dual-spin/frequency metasurface for quad-channel off-axis vortices multiplexing',
                'Confocal rescan structured illumination microscopy for real-time deep tissue imaging with superresolution',
                'Detection of trace metals in water by filament- and plasma-grating-induced breakdown spectroscopy',
                'Characterization of multimode linear optical networks',
                'Optical reflective metasurfaces based on mirror-coupled slot antennas',
                'On-chip tunable parity‐time symmetric optoelectronic oscillator',
                'Vortex-induced quasi-shear polaritons',
                'Anomalous broadband Floquet topological metasurface with pure site rings',
                'Deterministic <i>N</i>-photon state generation using lithium niobate on insulator device',
                'Ultrafast optical phase-sensitive ultrasonic detection via dual-comb multiheterodyne interferometry',
                'Laterally swept light-sheet microscopy enhanced by pixel reassignment for photon-efficient volumetric imaging',
                'Toward augmenting tip-enhanced nanoscopy with optically resolved scanning probe tips',
                'Supporting quantum technologies with an ultralow-loss silicon photonics platform',
                'Noncontact photoacoustic lipid imaging by remote sensing on first overtone of the C-H bond',
                'Scattered light imaging beyond the memory effect using the dynamic properties of thick turbid media',
                'Reflective optical vortex generators with ultrabroadband self-phase compensation',
                'High-speed hyperspectral imaging enabled by compressed sensing in time domain',
                'Controllable valley magnetic response in phase-transformed tungsten diselenide',
                'Nondiffractive three-dimensional polarization features of optical vortex beams',
                'Relative phase locking of a terahertz laser system configured with a frequency comb and a single-mode laser',
                'Realization of advanced passive silicon photonic devices with subwavelength grating structures developed by efficient inverse design',
                'Large-scale single-crystal blue phase through holography lithography',
                'Evolution on spatial patterns of structured laser beams: from spontaneous organization to multiple transformations',
                'Real-time monitoring of polarization state deviations with dielectric metasurfaces',
                'Self-seeded free-electron lasers with orbital angular momentum',
                'Fringe-pattern analysis with ensemble deep learning',
                'Deep image prior plus sparsity prior: toward single-shot full-Stokes spectropolarimetric imaging with a multiple-order retarder',
                'Direct laser-written aperiodic photonic volume elements for complex light shaping with high efficiency: inverse design and fabrication',
                'Structural designs of AlGaN/GaN nanowire-based photoelectrochemical photodetectors: carrier transport regulation in GaN segment as current flow hub',
                'Generation of high-efficiency, high-purity, and broadband Laguerre-Gaussian modes from a Janus optical parametric oscillator',
                'Reconfigurable structured light generation and its coupling to air–core fiber',
                'Low-insertion-loss femtosecond laser-inscribed three-dimensional high-density mux/demux devices',
                'High-repetition-rate seeded free-electron laser enhanced by self-modulation',
                'Long-range chaotic Brillouin optical correlation domain analysis with more than one million resolving points',
                'Statistical dynamics of noise-like rectangle pulse fiber laser',
                'Characteristics of a Gaussian focus embedded within spiral patterns in common-path interferometry with phase apertures',
                'Joint device architecture algorithm codesign of the photonic neural processing unit',
                'Multiparameter encrypted orbital angular momentum multiplexed holography based on multiramp helicoconical beams',
                'Multifunctional interface between integrated photonics and free space',
                'Complex-domain-enhancing neural network for large-scale coherent imaging',
                'Complete active–passive photonic integration based on GaN-on-silicon platform',
                'Printable organic light-emitting diodes for next-generation visible light communications: a review',
                'Review on near-field detection technology in the biomedical field',
                'Photoacoustic-enabled automatic vascular navigation: accurate and naked-eye real-time visualization of deep-seated vessels',
                'Generation and control of extreme ultraviolet free-space optical skyrmions with high harmonic generation',
                'Experimental optical computing of complex vector convolution with twisted light',
                'Untrained neural network enhances the resolution of structured illumination microscopy under strong background and noise levels',
                'Compact microring resonator based on ultralow-loss multimode silicon nitride waveguide',
                'Thermal camera based on frequency upconversion and its noise-equivalent temperature difference characterization',
                'Digital subcarrier multiplexing-enabled carrier-free phase-retrieval receiver',
                'Recent advances in deep-learning-enhanced photoacoustic imaging',
                'Achieving higher photoabsorption than group III-V semiconductors in ultrafast thin silicon photodetectors with integrated photon-trapping surface structures',
                'Differentiated design strategies toward broadband achromatic and polarization-insensitive metalenses',
                'Achromatic on-chip focusing of graphene plasmons for spatial inversions of broadband digital optical signals',
                'Operation of multiphonon-assisted laser in the nanosecond time scales',
                'Generation of biaxially accelerating static Airy light-sheets with 3D-printed freeform micro-optics',
                'Highly sensitive miniature needle PVDF-TrFE ultrasound sensor for optoacoustic microscopy',
                'Efficient reference-less transmission matrix retrieval for a multimode fiber using fast Fourier transform',
                'High-fidelity SIM reconstruction-based super-resolution quantitative FRET imaging',
                'High repetition rate ultrafast laser-structured nickel electrocatalyst for efficient hydrogen evolution reaction',
                'High-speed free-space optical communication using standard fiber communication components without optical amplification',
                'Robust moiré flatbands within a broad band-offset range',
                'Miniaturized short-wavelength infrared spectrometer for diffuse light applications',
                'Coordination engineering in Nd doped silica glass for improving repetition rate of 920-nm ultrashort-pulse fiber laser',
                'Nonconvex optimization for optimum retrieval of the transmission matrix of a multimode fiber',
                'High-quality-factor space–time metasurface for free-space power isolation at near-infrared regime',
                'Reconfigurable optical add-drop multiplexers for hybrid mode-/wavelength-division-multiplexing systems',
                'Advanced all-optical classification using orbital-angular-momentum-encoded diffractive networks',
                'Dissipative soliton breathing dynamics driven by desynchronization of orthogonal polarization states',
                'Coherently tiled Ti:sapphire laser amplification: a way to break the 10 petawatt limit on current ultraintense lasers',
                'Electromagnetic modeling of interference, confocal, and focus variation microscopy',
                'Terahertz probe for real time <i>in vivo</i> skin hydration evaluation',
                'Dual-channel quantum meta-hologram for display',
                'Complex-valued universal linear transformations and image encryption using spatially incoherent diffractive networks',
                'Experimental observation of topological large-area pseudo-spin-momentum-locking waveguide states with exceptional robustness',
                'Intense white laser of high spectral flatness via optical-damage-free water–lithium niobate module',
                'Carbon-based ultrabroadband tunable terahertz metasurface absorber',
                'Ultra-low-loss all-fiber orbital angular momentum mode-division multiplexer based on cascaded fused-biconical mode selective couplers',
                'Multidimensional multiplexing holography based on optical orbital angular momentum lattice multiplexing',
                'High-speed autopolarization synchronization modulation three-dimensional structured illumination microscopy',
                'Secure optical interconnects using orbital angular momentum beams multiplexing/multicasting',
                '100 Gb/s coherent chaotic optical communication over 800 km fiber transmission via advanced digital signal processing',
                'Spectrum shuttle for producing spatially shapable GHz burst pulses',
                'High-power, narrow linewidth solid-state deep ultraviolet laser generation at 193 nm by frequency mixing in LBO crystals',
                'Nonuniform pseudo-magnetic fields in photonic crystals',
                'Physics-constrained deep-inverse point spread function model: toward non-line-of-sight imaging reconstruction',
                'Multiparameter performance monitoring of pulse amplitude modulation channels using convolutional neural networks',
                'Unveiling optical rogue wave behavior with temporally localized structures in Brillouin random fiber laser comb',
                'Multimode diffractive optical neural network',
                'High spatial resolution collinear chiral sum-frequency generation microscopy',
                'Retrieving  Jones matrix from an imperfect metasurface polarizer',
                '635 nm femtosecond fiber laser oscillator and amplifier',
                'Generation of subwavelength inverted pin beam via fiber end integrated plasma structure',
                'Spectral transfer-learning-based metasurface design assisted by complex-valued deep neural network',
                'Azimuthal beam shaping in orbital angular momentum basis',
                'Generation of tunable high-order Laguerre–Gaussian petal-like modes from a mid-infrared optical vortex parametric oscillator',
                'High-performance silicon arrayed-waveguide grating (de)multiplexer with 0.4-nm channel spacing',
                'Photonic implementation of quantum gravity simulator Cover',
                'Simultaneous sorting of arbitrary vector structured beams with spin-multiplexed diffractive metasurfaces',
                'Random fiber laser using a cascaded fiber loop mirror',
                'Suppressing neuroinflammation using the near-infrared light emitted by (Sr,Ba)Ga<sub>12</sub>O<sub>19</sub>: Cr<sup>3+</sup> phosphor',
                'Beyond 200-Gb/s O-band intensity modulation and direct detection optics with joint look-up-table-based predistortion and digital resolution enhancement for low-cost data center interconnects',
                'Nonlinear localization of ultracold atomic Fermi gas in moiré optical lattices',
                'PC-bzip2: a phase-space continuity-enhanced lossless compression algorithm for light-field microscopy data',
                'Frequency-dependent selectively oriented edge state topological transport',
                'Integrated coherent beam combining system for orbital-angular-momentum shift-keying-based free-space optical links',
                'Single-wavelength size focusing of ultra-intense ultrashort lasers with rotational hyperbolic mirrors',
                'Split Lohmann computer holography: fast generation of 3D hologram in single-step diffraction calculation',
                'Enhanced terahertz generation via plasma modulation on two bunches',
                'Hybrid optical parametrically oscillating emitter-enabled photoacoustic imaging of water: enhanced contrast, dynamic range, and multifaceted applications',
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
