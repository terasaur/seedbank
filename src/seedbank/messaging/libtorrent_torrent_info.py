#
# Copyright 2012 ibiblio
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0.txt
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

class TorrentInfoPrinter(object):
    def out(self, ti):
        self._print_options(ti)

    def _print_options(self, ti):
        print 'private: %s' % ti.priv()

"""
    std::vector<announce_entry> const& trackers() const;

    int num_files() const;

    std::vector<std::string> const& url_seeds() const;
    std::vector<std::string> const& http_seeds() const;

    size_type total_size() const;
    int piece_length() const;
    int num_pieces() const;
    sha1_hash const& info_hash() const;
    std::string const& name() const;
    std::string const& comment() const;
    std::string const& creator() const;

    # DHT nodes
    std::vector<std::pair<std::string, int> > const& nodes() const;

    boost::optional<boost::posix_time::ptime> creation_date() const;

    int piece_size(unsigned int index) const;
    sha1_hash const& hash_for_piece(unsigned int index) const;

    std::vector<sha1_hash> const& merkle_tree() const;
"""
