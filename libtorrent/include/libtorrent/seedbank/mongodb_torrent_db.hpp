/**
 * Copyright 2012 ibiblio
 * All rights reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0.txt
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
#ifndef MONGODB_TORRENT_DB_HPP_INCLUDED
#define MONGODB_TORRENT_DB_HPP_INCLUDED

#ifdef _MSC_VER
#pragma warning(push, 1)
#endif

#include <boost/shared_ptr.hpp>
#include "libtorrent/config.hpp"
#include "libtorrent/extensions.hpp"
#include <map>

#ifdef _MSC_VER
#pragma warning(pop)
#endif

namespace libtorrent
{
    struct plugin;
    TORRENT_EXPORT boost::shared_ptr<plugin> create_mongodb_torrent_db_plugin(string_map const&);
}

#endif // MONGODB_TORRENT_DB_HPP_INCLUDED
