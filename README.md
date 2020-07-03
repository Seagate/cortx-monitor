[![Codacy Badge](https://app.codacy.com/project/badge/Grade/5a56c90ed9f8434287f54ccdcce0189b)](https://www.codacy.com?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=Seagate/cortx-sspl&amp;utm_campaign=Badge_Grade)

=> SSPL states
   ~~~~~~~~~~~

   -> Active state:
      When SSPL is in active state, all the configured plugins including Storage
      Enclosure monitoring and Node monitoring are working.

   -> Degraded state:
      In Degraded state, plugins responsible for Storage Enclosure monitoring
      are suspended. Plugins in this state run but don't check for platform
      components state change and no alerts are raised.

=> Steps to switch SSPL state
   ~~~~~~~~~~~~~~~~~~~~~~~~~~

   -> Switch to Active state:

      $ echo "state=active" > /var/cortx/sspl/data/state.txt
      $ kill -s SIGHUP <SSPL-PID>

   -> Switch to Degraded state:

      $ echo "state=degrade" > /var/cortx/sspl/data/state.txt
      $ kill -s SIGHUP <SSPL-PID>

=> Consul Configs
   ~~~~~~~~~~~~~~

   -> All product configs will be available through salt API's, then stored in consul in paticular format i.e.
      component/section/key = value where component = 'sspl/config'

   -> Get value from consul:

      consul kv get component/section/key
      Example: consul kv get sspl/config/NODEDATAMSGHANDLER/disk_usage_threshold

   -> Put(Update) value in consul:

      consul kv put sspl/config/NODEDATAMSGHANDLER/disk_usage_threshold $out
      Where key='sspl/config/NODEDATAMSGHANDLER/disk_usage_threshold' and value='$out'
