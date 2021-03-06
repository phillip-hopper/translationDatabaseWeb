import re
from copy import deepcopy

from bs4 import element, BeautifulSoup
import requests

from docutils.utils.smartquotes import smartyPants


HTML_TAG_RE = re.compile(ur"<.*?>", re.UNICODE)
LINK_TAG_RE = re.compile(ur"\[\[.*?\]\]", re.UNICODE)
IMG_TAG_RE = re.compile(ur"{{.*?}}", re.UNICODE)


def remove_html_comments(soup):
    """
    Remove HTML comments from incoming parsed html data

    :param soup: BeautifulSoup html.parser
    :type soup: object
    """
    is_html_comment = lambda text: isinstance(text, element.Comment)
    for html_comment in soup.find_all(text=is_html_comment):
        html_comment.extract()


def fix_dokuwiki_hyperlink_title_attr(soup):
    """
    Replace or set all title attributes of hyperlink elements in the html doc
    to the element text if the "en:ta:vol1:toc" type pattern is found.

    :param soup: BeautifulSoup html.parser
    :type soup: object

    :returns: object -- BeautifulSoup
    """
    for a_el in soup.find_all("a"):
        # Replace titles where the "en:ta:vol1:toc" pattern is found
        if a_el.get("title") and ":" in a_el.get("title"):
            a_el["title"] = a_el.text


def clean_text(input_text):
    """
    Cleans up text from possible dokuwiki and html tag polution

    :param input_text:
    :type input_text: str

    :returns: str
    """
    output_text = HTML_TAG_RE.sub(u"", input_text)
    output_text = LINK_TAG_RE.sub(u"", output_text)
    output_text = IMG_TAG_RE.sub(u"", output_text)
    return output_text


class OpenBibleStory(object):
    """
    Fetch and parse the OpenBibleStory content from door43
    """

    img_link_re = re.compile(ur"https://.*\.(jpg|jpeg|gif)", re.UNICODE)
    title_re = re.compile(ur"======.*", re.UNICODE)
    ref_re = re.compile(ur"//.*//", re.UNICODE)
    frame_re = re.compile(ur"{{[^{]*", re.DOTALL | re.UNICODE)
    frid_re = re.compile(ur"[0-5][0-9]-[0-9][0-9]", re.UNICODE)
    num_re = re.compile(ur"([0-5][0-9]).txt", re.UNICODE)
    chapter_numbers = ["{0:02}".format(x) for x in range(1, 51)]
    img_url = "https://api.unfoldingword.org/obs/jpg/1/{0}/360px/obs-{0}-{1}.jpg"
    source_url = "https://door43.org/{lang_code}/obs/{chapter}?do=export_raw"

    def __init__(self, lang_code):
        self.lang_code = lang_code
        self.session = requests.session()

    def _parse(self, regex, raw, replace):
        values = regex.search(raw)
        return values.group(0).replace(replace, "").strip() if values else "NOT FOUND"

    def _parse_img(self, link, frame_id):
        links = self.img_link_re.search(link)
        return links.group(0) if links else self.img_url.format("en", frame_id)

    def _parse_frame_text(self, lines):
        text = u"".join([x for x in lines[1:] if u"//" not in x]).strip()
        text = text.replace(u"\\\\", u"").replace(u"**", u"").replace(u"__", u"")
        text = clean_text(text)
        text = smartyPants(text)
        return text

    def _fetch_matter(self, prefix):
        """
        Fetch the front and back matter content for OBS

        :param prefix: 'front' or 'back'
        :type prefix: str

        :returns: dict
        """
        matter = "{0}-matter".format(prefix)
        ret = {"id": matter, "text": None}
        resp = self.session.get(
            self.source_url.format(
                lang_code=self.lang_code,
                chapter=matter
            )
        )
        if resp.ok:
            ret["text"] = self._parse_frame_text(resp.text)
        return ret

    def fetch_chapter(self, chapter_number):
        chapter_data = {"frames": [], "number": chapter_number, "ref": "", "title": ""}
        response = self.session.get(
            self.source_url.format(
                lang_code=self.lang_code,
                chapter=chapter_number)
        )
        response.encoding = "utf-8"
        if response.status_code == 200:
            chapter_raw = response.text
            chapter_data["title"] = self._parse(self.title_re, chapter_raw, "=")
            chapter_data["ref"] = self._parse(self.ref_re, chapter_raw, "/")
            for frame in self.frame_re.findall(chapter_raw):
                frame_lines = frame.split("\n")
                frame_ids = self.frid_re.search(frame)
                frame_id = frame_ids.group(0) if frame_ids else "NOT FOUND"
                chapter_data["frames"].append({
                    "id": frame_id,
                    "img": self._parse_img(frame_lines[0], frame_id),
                    "text": self._parse_frame_text(frame_lines[1:])
                })
        return chapter_data

    def fetch_chapters(self):
        chapters = [
            self.fetch_chapter(chapter_number)
            for chapter_number in self.chapter_numbers
        ]
        return {
            "chapters": chapters,
            "front_matter": self._fetch_matter(prefix="front"),
            "back_matter": self._fetch_matter(prefix="back"),
        }


class TranslationAcademy(object):
    """
    Traverse translationAcademy on door43.org, fetching the table of contents
    and then each topic and contents.
    """

    # chapter document IDs in the table of contents
    CHAPTERS = [
        "plugin_include__en__ta__vol1__intro__toc_intro",
        "plugin_include__en__ta__vol1__translate__toc_transvol1",
        "plugin_include__en__ta__vol1__checking__toc_checkvol1",
        "plugin_include__en__ta__vol1__tech__toc_techvol1",
        "plugin_include__en__ta__vol1__process__toc_processvol1",
    ]

    source_url = "https://door43.org{uri}"
    chapters_uri = "/{lang_code}/ta/vol{vol_no}/toc"

    def __init__(self, lang_code, volume_number=1):
        self.lang_code = lang_code
        self.session = requests.session()
        self.session.params = {"do": "export_xhtmlbody"}
        self.volume_number = str(volume_number)

    def _parse_frames(self, soup):
        """
        Fetch the frame content from the hyperlink in the list element, then
        check for sub-frames in any child list elements.

        :param soup: HTML results of the TOC listing via BeautifulSoup
        :type soup: object

        :returns: list
        """
        frames = []
        sub_frames = []

        for a_el in soup.find_all("a"):
            # @TODO - There is a better way...
            li_classes = a_el.find_previous("li").get("class")
            li_lvl = int(li_classes[0].lstrip("level"))
            frame = self.fetch_frame(a_el.get("href"))
            if li_lvl == 1:
                if sub_frames:
                    frames[-1]["frames"] = deepcopy(sub_frames)
                    sub_frames = []
                frames.append(frame)
            elif li_lvl == 2:
                sub_frames.append(frame)
            elif li_lvl == 3:
                if "frames" not in sub_frames[-1]:
                    sub_frames[-1]["frames"] = []
                sub_frames[-1]["frames"].append(frame)

        if sub_frames:
            frames[-1]["frames"] = sub_frames
        return frames

    def _parse_table_of_contents(self, soup):
        """
        Traverse HTML results via BeautifulSoup, returning the table of
        contents

        :param soup: HTML results of the TOC listing via BeautifulSoup
        :type soup: object

        :returns: dict
        """
        page_header_el = soup.find("h2")
        toc = {
            "title": page_header_el.text,
            "id": page_header_el.get("id"),
            "chapters": [],
        }

        # Iterate over each section of the TOC, grabbing the header element's
        # text as the chapter's title, then fetching all links inside the
        # chapter.
        for chapter_id in self.CHAPTERS:
            chapter_el = soup.find(id=chapter_id)
            if not chapter_el:
                continue

            # Get the chapter's title
            title = chapter_el.find_next(("h4", "h3")).text
            chapter = {"title": title.replace("Table of Contents - ", "")}

            # Find frames under the chapter
            frames = []
            for frame_header in chapter_el.find_all("h4"):
                el = frame_header.find_next_sibling("div")
                for frame in self._parse_frames(el):
                    frames.append(frame)

            if frames:
                chapter["frames"] = frames

            # Find sections (with frames) under the chapter
            sections = []
            for section_header in chapter_el.find_all("h5"):
                el = section_header.find_next_sibling("div")
                section_frames = self._parse_frames(el)
                if section_frames:
                    sections.append({
                        "id": el.get("id"),
                        "title": section_header.text,
                        "frames": section_frames
                    })

            if sections:
                chapter["sections"] = sections

            toc["chapters"].append(chapter)
        return toc

    def fetch_frame(self, frame_uri):
        """
        Fetch the content from the `frame_uri`, parsing and formatting the
        input into one expected by the publishing module.

        :param chapter_uri: URI for frame of translationAcademy
        :type chapter_uri: string

        :returns: dict
        """
        frame_url = self.source_url.format(uri=frame_uri)
        response = self.session.get(frame_url)

        if response.ok:
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove HTML comment elements, specifically those from dokuwiki
            remove_html_comments(soup)
            # Replaces the hyperlink title attribute values like:
            # "en:ta:vol1:translate:translate_retell" to the hyperlink text
            fix_dokuwiki_hyperlink_title_attr(soup)

            # Find the page title header
            title_el = soup.find(("h1", "h2", "h3"))
            return {
                "id": title_el.get("id"),
                "ref": frame_uri,
                "title": title_el.text.replace("Table of Contents - ", ""),
                "text": soup.prettify(formatter="html"),
            }

    def fetch_chapters(self):
        """
        Fetch and parse the table of contents page for translationAcademy

        :returns: dict
        """
        chapters_uri = self.chapters_uri.format(
            lang_code=self.lang_code,
            vol_no=self.volume_number
        )
        chapters_url = self.source_url.format(uri=chapters_uri)
        response = self.session.get(chapters_url)
        if not response.ok:
            response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        return self._parse_table_of_contents(soup)


RESOURCE_TYPES = {
    "obs": OpenBibleStory,
    "ta": TranslationAcademy,
}
