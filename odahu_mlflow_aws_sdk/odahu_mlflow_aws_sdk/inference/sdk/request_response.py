#
#    Copyright 2021 EPAM Systems
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#
import typing


class PredictionRequestResponse:
    """
    Container for prediction request / response
    """
    def __init__(self,
                 content: typing.Union[str, bytes, typing.BinaryIO, typing.TextIO],
                 content_type: typing.Optional[str] = None,
                 attributes: typing.Optional[typing.Dict[str, object]] = None):
        self._content = content
        self._content_type = content_type
        self._attributes = attributes
        self._content_read = isinstance(content, (str, bytes))

    def _read_content(self) -> typing.Union[str, bytes]:
        if not self._content_read:
            self._content = self._content.read()
            self._content_read = True
        return self._content

    @property
    def content_type(self) -> typing.Optional[str]:
        return self._content_type

    @property
    def as_headers(self):
        headers = {}
        if self.content_type:
            headers['Content-Type'] = self.content_type
        return headers

    @property
    def attributes(self) -> typing.Optional[typing.Dict[str, object]]:
        return self._attributes

    @property
    def content_str(self):
        data = self._read_content()
        if not isinstance(data, str):
            data = self._content.decode('utf-8')
        return data
