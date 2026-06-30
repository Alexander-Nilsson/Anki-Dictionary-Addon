import collections
import re


class NoteAssembler:
    def __init__(self, mw, html_cleaner):
        self._mw = mw
        self._html_cleaner = html_cleaner

    @staticmethod
    def field_valid(field):
        return field != "Don't Export"

    @staticmethod
    def empty_value_if_empty_html(value):
        pattern = r"(?:<[^<]+?>)"
        if re.sub(pattern, "", value) == "":
            return ""
        return value

    @staticmethod
    def get_dictionary_entries(definition_list, dictionary):
        fin_list = []
        idxs = []
        for idx, def_list in enumerate(definition_list):
            if def_list[0] == dictionary:
                fin_list.append(def_list[2])
                idxs.append(idx)
        idxs.reverse()
        for idx in idxs:
            definition_list.pop(idx)
        return fin_list

    def get_dictionary_name_to_table_name_dictionary(self):
        dict_to_table = collections.OrderedDict()
        dict_to_table["None"] = "None"
        dict_to_table["Images"] = "Images"
        for dict_table_name in sorted(self._mw.miDictDB.getAllDicts()):
            dict_name = self._mw.miDictDB.cleanDictName(dict_table_name)
            dict_to_table[dict_name] = dict_table_name
        return dict_to_table

    def assemble_field_values(
        self,
        template,
        sentence_html,
        secondary_html,
        notes_html,
        word_text,
        tags_text,
        definition_list,
        img_name,
        audio_tag,
        image_map_text,
        audio_map_text,
    ):
        img_field = False
        audio_field = False
        tags_field = ""
        fields = {}
        sentence_text = self._html_cleaner.cleanHTML(sentence_html)
        sentence_text = self.empty_value_if_empty_html(sentence_text)
        if sentence_text != "":
            sentence_field = template["sentence"]
            if sentence_field != "Don't Export":
                if self.field_valid(sentence_field):
                    fields[sentence_field] = [sentence_text]
        secondary_text = self._html_cleaner.cleanHTML(secondary_html)
        secondary_text = self.empty_value_if_empty_html(secondary_text)
        if secondary_text != "" and "secondary" in template:
            secondary_field = template["secondary"]
            if secondary_field != "Don't Export":
                if self.field_valid(secondary_field):
                    fields[secondary_field] = [secondary_text]
        notes_text = self._html_cleaner.cleanHTML(notes_html)
        notes_text = self.empty_value_if_empty_html(notes_text)
        if notes_text != "" and "notes" in template:
            notes_field = template["notes"]
            if notes_field != "Don't Export":
                if self.field_valid(notes_field):
                    fields[notes_field] = [notes_text]
        if word_text != "":
            word_field = template["word"]
            if word_field != "Don't Export":
                if self.field_valid(word_field):
                    if word_field not in fields:
                        fields[word_field] = [word_text]
                    else:
                        fields[word_field].append(word_text)
        if tags_text != "":
            tags_field = tags_text
        if image_map_text != "No Image Selected":
            img_field = template["image"]
            if img_field != "Don't Export":
                img_tag = '<img ankiDict="' + img_name + '">'
                if self.field_valid(img_field):
                    if img_field not in fields:
                        fields[img_field] = [img_tag]
                    else:
                        fields[img_field].append(img_tag)
        if (
            audio_map_text != "No Audio Selected"
            and "audio" in template
            and audio_tag is not False
        ):
            audio_field = template["audio"]
            if audio_field != "Don't Export":
                if self.field_valid(audio_field):
                    if audio_field not in fields:
                        fields[audio_field] = [audio_tag]
                    else:
                        fields[audio_field].append(audio_tag)
        specific = template["specific"]
        for field in specific:
            for dictionary in specific[field]:
                if field not in fields:
                    fields[field] = self.get_dictionary_entries(
                        definition_list, dictionary
                    )
                else:
                    fields[field] += self.get_dictionary_entries(
                        definition_list, dictionary
                    )
        unspecified = template["unspecified"]
        for _idx, def_list in enumerate(definition_list):
            if unspecified not in fields:
                fields[unspecified] = [def_list[2]]
            else:
                fields[unspecified].append(def_list[2])
        return fields, img_field, audio_field, tags_field

    def assemble_for_text_card(self, template, word_text, sentence_text, tags_text):
        tags_field = ""
        fields = {}
        if sentence_text != "":
            sentence_field = template["sentence"]
            if sentence_field != "Don't Export":
                if self.field_valid(sentence_field):
                    fields[sentence_field] = [sentence_text]
        if word_text != "":
            word_field = template["word"]
            if word_field != "Don't Export":
                if self.field_valid(word_field):
                    if word_field not in fields:
                        fields[word_field] = [word_text]
                    else:
                        fields[word_field].append(word_text)
        if tags_text != "":
            tags_field = tags_text
        return fields, tags_field

    def assemble_for_media_card(self, template, word_text, card, tags_text):
        sentence_text = card["primary"]
        secondary_text = card["secondary"]
        image_file = card["image"]
        audio_file = card["audio"]
        audio = False
        image = False
        if audio_file:
            audio = "[sound:" + audio_file + "]"
        if image_file:
            image = image_file
        img_field = False
        audio_field = False
        fields = {}
        tags_field = ""
        if sentence_text != "":
            sentence_field = template["sentence"]
            if sentence_field != "Don't Export":
                if self.field_valid(sentence_field):
                    fields[sentence_field] = [sentence_text]
        if secondary_text != "" and "secondary" in template:
            secondary_field = template["secondary"]
            if secondary_field != "Don't Export":
                if self.field_valid(secondary_field):
                    fields[secondary_field] = [secondary_text]
        if word_text != "":
            word_field = template["word"]
            if word_field != "Don't Export":
                if self.field_valid(word_field):
                    if word_field not in fields:
                        fields[word_field] = [word_text]
                    else:
                        fields[word_field].append(word_text)
        if tags_text != "":
            tags_field = tags_text
        if image:
            img_field = template["image"]
            img_tag = '<img ankiDict="' + image + '">'
            if self.field_valid(img_field):
                if img_field not in fields:
                    fields[img_field] = [img_tag]
                else:
                    fields[img_field].append(img_tag)
        if audio:
            audio_field = template["audio"]
            if self.field_valid(audio_field):
                if audio_field not in fields:
                    fields[audio_field] = [audio]
                else:
                    fields[audio_field].append(audio)
        return fields, tags_field

    def auto_add_definitions(self, note, word, template, definition_settings):
        if not definition_settings:
            return note
        dict_to_table = self.get_dictionary_name_to_table_name_dictionary()
        unspecified_definition_field = template["unspecified"]
        specific_fields = template["specific"]
        dictionaries = []
        for setting in definition_settings:
            dict_name = setting["name"]
            if dict_name in dict_to_table:
                table = dict_to_table[dict_name]
                limit = setting["limit"]
                target_field = unspecified_definition_field
                for specific_field, specific_dictionaries in specific_fields.items():
                    if dict_name in specific_dictionaries:
                        target_field = specific_field
                dictionaries.append(
                    {
                        "tableName": table,
                        "limit": limit,
                        "field": target_field,
                        "dictName": dict_name,
                    }
                )
        return self._mw.addDefinitionsToCardExporterNote(note, word, dictionaries)
