"""初始化本地语料库：生成 local_corpus.json 供离线引擎测试。

运行方式：python init_corpus.py
"""

import json
from pathlib import Path

CORPUS_PATH = Path(__file__).resolve().parent / "local_corpus.json"

SAMPLE_ARTICLES = [
    {
        "title": "The Solar System",
        "content": (
            "The Solar System consists of the Sun and the celestial objects that are bound to it by gravity. "
            "These objects include eight planets, their moons, dwarf planets, asteroids, comets, and other small bodies. "
            "The four inner planets — Mercury, Venus, Earth, and Mars — are terrestrial, meaning they have solid, rocky surfaces. "
            "The four outer planets — Jupiter, Saturn, Uranus, and Neptune — are gas or ice giants with thick atmospheres. "
            "Earth is the only known planet to support life, thanks to its unique combination of liquid water, moderate temperatures, "
            "and a protective atmosphere. The Sun, a medium-sized star, provides the energy that drives weather, ocean currents, "
            "and biological processes on Earth. Scientists continue to explore the Solar System using telescopes, space probes, "
            "and robotic rovers, hoping to uncover clues about the origins of our cosmic neighborhood and the possibility of life elsewhere."
        ),
    },
    {
        "title": "The History of the Internet",
        "content": (
            "The Internet began as a United States military project in the late 1960s called ARPANET, designed to allow researchers "
            "at different universities to share computing resources. By the 1980s, the network had expanded beyond the military to "
            "include academic institutions worldwide. The invention of the World Wide Web by Tim Berners-Lee in 1989 transformed the "
            "Internet from a tool for specialists into a global communication platform accessible to ordinary people. "
            "The introduction of web browsers in the early 1990s made it possible for anyone with a computer and a phone line to "
            "explore websites, send emails, and participate in online forums. Today, the Internet connects billions of devices and "
            "supports everything from e-commerce and social media to cloud computing and artificial intelligence. "
            "However, it also raises concerns about privacy, cybersecurity, misinformation, and digital inequality. "
            "Governments and organizations around the world are working to address these challenges while preserving the open nature "
            "of the Internet that has fueled innovation for decades."
        ),
    },
    {
        "title": "Climate Change and Its Global Impact",
        "content": (
            "Climate change refers to long-term shifts in global temperatures and weather patterns. While some changes are natural, "
            "scientific evidence overwhelmingly shows that human activities — particularly the burning of fossil fuels like coal, oil, "
            "and natural gas — have been the primary driver of climate change since the industrial revolution. "
            "The release of greenhouse gases, such as carbon dioxide and methane, traps heat in the atmosphere, leading to a gradual "
            "increase in the Earth's average temperature known as global warming. The consequences include rising sea levels, more "
            "frequent and severe storms, prolonged droughts, shrinking ice caps, and disruptions to ecosystems. "
            "Many species face extinction as their habitats change faster than they can adapt. "
            "International agreements, such as the Paris Agreement of 2015, aim to limit global warming to 1.5 degrees Celsius above "
            "pre-industrial levels. Achieving this goal requires rapid reductions in emissions, a transition to renewable energy "
            "sources, and significant changes in agriculture, transportation, and industry. Individual actions — such as reducing "
            "energy consumption, choosing sustainable products, and supporting climate-friendly policies — also play an important role."
        ),
    },
    {
        "title": "Artificial Intelligence in Modern Society",
        "content": (
            "Artificial intelligence, commonly known as AI, refers to computer systems designed to perform tasks that typically "
            "require human intelligence, such as understanding language, recognizing images, making decisions, and learning from "
            "experience. The field has its roots in the 1950s, but recent advances in computing power and the availability of large "
            "datasets have led to breakthroughs in machine learning and deep learning. "
            "Today, AI powers a wide range of applications, from virtual assistants like Siri and Alexa to recommendation algorithms "
            "on platforms like Netflix and YouTube. In healthcare, AI helps doctors diagnose diseases earlier and develop personalized "
            "treatment plans. In transportation, self-driving cars use AI to navigate roads safely. "
            "Despite its benefits, AI raises ethical concerns. Issues such as algorithmic bias, job displacement, and the potential "
            "misuse of autonomous weapons have sparked intense debate among researchers, policymakers, and the public. "
            "Experts agree that responsible development, transparent governance, and inclusive dialogue are essential to ensuring that "
            "AI serves humanity rather than harming it."
        ),
    },
    {
        "title": "The Water Cycle and Freshwater Resources",
        "content": (
            "The water cycle, also known as the hydrological cycle, describes the continuous movement of water on, above, and below "
            "the surface of the Earth. It involves several key processes: evaporation, condensation, precipitation, infiltration, and "
            "runoff. Water evaporates from oceans, lakes, and rivers, rises into the atmosphere as vapor, condenses into clouds, and "
            "eventually falls back to the surface as rain or snow. Some of this water seeps into the ground to replenish underground "
            "aquifers, while the rest flows into streams and rivers, eventually returning to the ocean. "
            "Freshwater is essential for drinking, agriculture, sanitation, and industry, yet it accounts for only about 2.5 percent "
            "of the Earth's total water supply. Much of this freshwater is locked in glaciers and ice caps, leaving less than one "
            "percent readily available for human use. "
            "Population growth, urbanization, pollution, and climate change are putting increasing pressure on freshwater resources. "
            "Water scarcity already affects more than two billion people worldwide. Sustainable water management, including efficient "
            "irrigation, wastewater treatment, and conservation efforts, is critical to ensuring access to clean water for future "
            "generations."
        ),
    },
]


def main() -> None:
    CORPUS_PATH.write_text(
        json.dumps(SAMPLE_ARTICLES, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[OK] Generated test corpus: {CORPUS_PATH}")
    print(f"     Contains {len(SAMPLE_ARTICLES)} articles:")
    for i, article in enumerate(SAMPLE_ARTICLES, 1):
        print(f"     {i}. {article['title']}")


if __name__ == "__main__":
    main()
