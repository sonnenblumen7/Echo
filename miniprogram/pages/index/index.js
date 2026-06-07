Page({
  startProtection() {
    console.log('点击开启守护')

    wx.getLocation({
      type: 'wgs84',
      success(res) {
        console.log('getLocation 成功:', res)

        const now = Math.floor(Date.now() / 1000)

        wx.request({
          url: 'http://192.168.1.21:8000/heartbeat',
          method: 'POST',
          header: { 'Content-Type': 'application/json' },
          data: [
            {
              device_id: 'test_device_01',
              latitude: res.latitude,
              longitude: res.longitude,
              client_ts: now,
              type: 'physical'
            }
          ],
          success(r) {
            console.log('POST /heartbeat 成功:', r.data)
            wx.showToast({ title: '心跳发送成功', icon: 'success' })
          },
          fail(err) {
            console.log('POST /heartbeat 失败:', err)
            wx.showToast({ title: '发送失败', icon: 'error' })
          }
        })
      },
      fail(err) {
        console.log('getLocation 失败:', err)
        wx.showToast({ title: '定位失败', icon: 'error' })
      }
    })
  }
})
