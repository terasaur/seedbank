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

#include "libtorrent/pch.hpp"

#ifdef _MSC_VER
#pragma warning(push, 1)
#endif

#include <boost/shared_ptr.hpp>

#ifdef _MSC_VER
#pragma warning(pop)
#endif

#include "libtorrent/seedbank/mongodb_torrent_db.hpp"
#include "libtorrent/seedbank/mongodb_alert_code.hpp"
#include "libtorrent/session.hpp"
#include "libtorrent/aux_/session_impl.hpp"
#include "libtorrent/extensions.hpp"
#include "libtorrent/peer_id.hpp" // sha1_hash
#include "libtorrent/escape_string.hpp" // to_hex
#include "libtorrent/error_code.hpp"
#include "libtorrent/torrent.hpp"
#include "libtorrent/alert.hpp"
#include "libtorrent/alert_types.hpp"

#include <mongo/client/dbclient.h> // mongodb client
#include <sstream>

using std::string;
using std::stringstream;

#if !defined TORRENT_DISABLE_EXTENSIONS

// Set to 1 for debugging
#define MONGODB_PLUGIN_DEBUG 0

namespace libtorrent {

    class peer_connection;

    struct TORRENT_EXPORT mongodb_plugin_alert: alert
    {
        mongodb_plugin_alert(int c , std::string const& m)
            : code(c)
            , msg(m)
        {
            TORRENT_ASSERT(!m.empty());
        }

        TORRENT_DEFINE_ALERT(mongodb_plugin_alert);
        const static int static_category = alert::error_notification | alert::status_notification;

        std::string message() const {
            char ret[400];
            snprintf(ret, sizeof(ret), "(%d) %s", code, msg.c_str());
            return ret;
        }

        int code;
        std::string msg;
    };

namespace
{
    struct mongodb_torrent_db_plugin : plugin
    {
        mongodb_torrent_db_plugin(string_map const& param_map)
        {
            _set_param_or_default(param_map, "connection_string", "localhost:27017");
            _set_param_or_default(param_map, "torrentdb_ns", "seedbank.torrent");
            _set_param_or_default(param_map, "torrent_file_root", "/var/lib/seedbank/torrents");
        }

        void _set_param_or_default(string_map const& param_map, string const& key, string const& default_value)
        {
            string_map::const_iterator iter = param_map.find(key);
            if (iter != param_map.end()) {
                m_param_map[key] = iter->second;
            } else {
                m_param_map[key] = default_value;
            }
        }

        virtual void added(boost::weak_ptr<aux::session_impl> s)
        {
            m_ses = s;
            boost::shared_ptr<aux::session_impl> ses;
            ses = m_ses.lock();

            // make initial connection to mongodb
            try {
                m_db_connection.connect(m_param_map["connection_string"]);
                if (ses->m_alerts.should_post<mongodb_plugin_alert>())
                {
                    ses->m_alerts.post_alert(mongodb_plugin_alert(mongodb_alert_code::db_connect_ok, "mongodb connection okay"));
                }
            } catch (mongo::DBException &e) {
                if (ses->m_alerts.should_post<mongodb_plugin_alert>())
                {
                    ses->m_alerts.post_alert(mongodb_plugin_alert(mongodb_alert_code::db_connect_error, e.what()));
                }
            }
        }

        /**
         * Function executed after session::find_torrent looks through internal
         * torrent map for an info_hash.  If not found, perform lookup in mongodb
         * for the torrent.  If found, activate the torrent in the session and set
         * the torrent pointer before returning.
         *
         * use_extended_pool controls executing lookups in a backend torrent database
         *		via a plugin::on_find_torrent call.  This is important to avoid an
         *		infinite call loop when activating offline torrents.
         */
        virtual boost::weak_ptr<torrent> on_find_torrent(sha1_hash const& info_hash, boost::weak_ptr<torrent> t_old, bool use_extended_pool)
        {
#if MONGODB_PLUGIN_DEBUG
            std::cout << "on_find_torrent (" << info_hash << ", " << use_extended_pool << ")" << std::endl;
#endif
            boost::weak_ptr<torrent> t_new;
            try {
                // Only look for torrent if one was not already found
                if (use_extended_pool && t_old.expired()) {
                    t_new = _find_and_add_torrent(info_hash);
                } else {
                    t_new = t_old;
                }
            } catch (std::exception& e) {
                boost::shared_ptr<aux::session_impl> ses;
                ses = m_ses.lock();
                if (ses->m_alerts.should_post<mongodb_plugin_alert>())
                {
                    stringstream ss;
                    ss << "ERROR: caught exception in on_find_torrent: " << e.what();
                    ses->m_alerts.post_alert(mongodb_plugin_alert(mongodb_alert_code::unclassified_error, ss.str()));
                }
                t_new = t_old;
            }
            return t_new;
        }

    private:
        string_map m_param_map;
        mongo::DBClientConnection m_db_connection;
        boost::weak_ptr<aux::session_impl> m_ses;

        /**
         *
         */
        virtual boost::weak_ptr<torrent> _find_and_add_torrent(sha1_hash const& info_hash)
        {
#if MONGODB_PLUGIN_DEBUG
            std::cout << "_find_and_add_torrent (" << info_hash << ")" << std::endl;
#endif
            boost::weak_ptr<torrent> new_torrent;
            boost::shared_ptr<aux::session_impl> ses;
            ses = m_ses.lock();

            mongo::BSONObj torrent_record;
            boost::intrusive_ptr<torrent_info> ti;
            torrent_record = _look_up_info_hash(ses, info_hash);

            string ih_hex;
            string data_root;
            if (torrent_record["info_hash"].ok()) {
                ih_hex = torrent_record["info_hash"].str();
            }
            if (torrent_record["data_root"].ok()) {
                data_root = torrent_record["data_root"].str();
            }

            if (!ih_hex.empty()) {
                ti = _convert_to_torrent_info(ses, ih_hex);
            }

            if (ti && ti.get()) {
#if MONGODB_PLUGIN_DEBUG
            std::cout << "found torrent, about to add to session" << std::endl;
#endif
                torrent_handle th = _activate_torrent(ses, ti, data_root);

                // Seems like there should be a way to get a torrent from a torrent_handle,
                // but there's not.
                std::map<sha1_hash, boost::shared_ptr<torrent> >::iterator i = ses->m_torrents.find(info_hash);
                if (i != ses->m_torrents.end()) {
                    new_torrent = i->second;
                    boost::shared_ptr<torrent> t_shared = new_torrent.lock();

                    // disable communication with trackers by clearing the list
                    std::vector<announce_entry> tracker_list = std::vector<announce_entry>();
                    t_shared->replace_trackers(tracker_list);

                    // force into seeding state
                    t_shared->completed();

                    // setup complete, enable connections
                    // allow_peers = true, graceful_pause_mode = false
                    t_shared->set_allow_peers(true, false);

                    if (ses->m_alerts.should_post<mongodb_plugin_alert>())
                    {
                        stringstream ss;
                        ss << "Activated new torrent: " << ih_hex;
                        ses->m_alerts.post_alert(mongodb_plugin_alert(mongodb_alert_code::torrent_activated, ss.str()));
                    }
                } else {
                    if (ses->m_alerts.should_post<mongodb_plugin_alert>())
                    {
                        stringstream ss;
                        ss << "ERROR: didn't find torrent in ses.m_torrents: " << ih_hex;
                        ses->m_alerts.post_alert(mongodb_plugin_alert(mongodb_alert_code::unclassified_error, ss.str()));
                    }
                }
            } else {
                if (ses->m_alerts.should_post<mongodb_plugin_alert>())
                {
                    stringstream ss;
                    ss << "ERROR: got null torrent_info from look_up_torrent: " << ih_hex;
                    ses->m_alerts.post_alert(mongodb_plugin_alert(mongodb_alert_code::unclassified_error, ss.str()));
                }
            }

            return new_torrent;
        }

        /**
         * Query mongodb for given info_hash.  Return BSONObj if found, null otherwise.
         */
        virtual mongo::BSONObj _look_up_info_hash(
            boost::shared_ptr<aux::session_impl> ses,
            sha1_hash const& info_hash)
        {
            mongo::BSONObj torrent_record;
            char ih_hex[41];
            to_hex((char const*)&info_hash[0], sha1_hash::size, ih_hex);

            if (m_db_connection.isFailed()) {
                if (ses->m_alerts.should_post<mongodb_plugin_alert>())
                {
                    stringstream ss;
                    ss << "Connection in failed state: " << ih_hex;
                    ses->m_alerts.post_alert(mongodb_plugin_alert(mongodb_alert_code::db_connection_failed, ss.str()));
                }
            } else {
                std::auto_ptr<mongo::DBClientCursor> cursor = m_db_connection.query(m_param_map["torrentdb_ns"], QUERY("info_hash" << ih_hex));
                bool found_results = false;

                while (cursor->more()) {
                    // TODO: verify no more than one record returned?
                    torrent_record = cursor->next();
                    found_results = true;
                }

                if (!found_results) {
                    if (ses->m_alerts.should_post<mongodb_plugin_alert>())
                    {
                        stringstream ss;
                        ss << "Torrent not found: " << ih_hex;
                        ses->m_alerts.post_alert(mongodb_plugin_alert(mongodb_alert_code::torrent_not_found, ss.str()));
                    }
                }
            }
            return torrent_record;
        }

        /**
         * Create torrent_info object for given info_hash.  This comes after a
         * successful lookup in mongodb.
         */
        virtual boost::intrusive_ptr<torrent_info> _convert_to_torrent_info(boost::shared_ptr<aux::session_impl> ses, string const& ih_hex)
        {
            // TODO: assert valid info hash
            if (ih_hex.empty()) {
                if (ses->m_alerts.should_post<mongodb_plugin_alert>())
                {
                    stringstream ss;
                    ss << "ERROR: got empty ih_hex in _convert_to_torrent_info";
                    ses->m_alerts.post_alert(mongodb_plugin_alert(mongodb_alert_code::unclassified_error, ss.str()));
                }
            }

            stringstream torrent_file;
            string subpath = _get_torrent_subpath(ih_hex);

            torrent_file << m_param_map["torrent_file_root"] << subpath << "/" << ih_hex << ".torrent";

            boost::intrusive_ptr<torrent_info> ti;
            try {
                ti = boost::intrusive_ptr<torrent_info>(new torrent_info(torrent_file.str()));
            } catch (invalid_torrent_file e) {
                if (ses->m_alerts.should_post<mongodb_plugin_alert>())
                {
                    stringstream ss;
                    ss << "Exception from new torrent_info (" << e.what() << ") when adding torrent " << ih_hex << " (" << torrent_file.str() << ")";
                    ses->m_alerts.post_alert(mongodb_plugin_alert(mongodb_alert_code::invalid_torrent_file, ss.str()));
                }
            }

            return ti;
        }

        /**
         * Derive subdivided directory path from hex info hash string.
         * e.g. 311edf6121b1f365201520f914219b5cec9890ae -> /3/1/1/e
         */
        virtual string _get_torrent_subpath(string ih_hex)
        {
            // TODO: Fetch levels value from config location
            int subpath_levels = 4;
            stringstream subpath;
            for (int i = 0; i < subpath_levels; ++i) {
                subpath << "/" << ih_hex.substr(i,1);
            }
            return subpath.str();
        }

        virtual torrent_handle _activate_torrent(
            boost::shared_ptr<aux::session_impl> ses,
            boost::intrusive_ptr<torrent_info> ti, string const& data_root)
        {
            add_torrent_params params;
            params.ti = ti;
            params.save_path = data_root;
            params.paused = true; // pause until setup is complete
            params.auto_managed = false;
            params.seed_mode = true;
            params.override_resume_data = true;
            params.upload_mode = true;

            // for debugging:
            params.duplicate_is_error = true;

            error_code ec;
            torrent_handle th = ses->add_torrent(params, ec);

            // TODO: What to do with ec > no_error here?
            if (ec) {
                if (ses->m_alerts.should_post<mongodb_plugin_alert>())
                {
                    stringstream ss;
                    ss << "ERROR: ec from session_impl::add_torrent: " << ec;
                    ses->m_alerts.post_alert(mongodb_plugin_alert(mongodb_alert_code::unclassified_error, ss.str()));
                }
            }

            return th;
        }

    };
} }

namespace libtorrent
{
    boost::shared_ptr<plugin> create_mongodb_torrent_db_plugin(string_map const& param_map)
    {
        return boost::shared_ptr<plugin>(new mongodb_torrent_db_plugin(param_map));
    }
}

#endif

