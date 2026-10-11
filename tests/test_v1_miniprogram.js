const assert = require('assert');
let page, stored = {token:'test-token'};
let latest = {latitude:31.2,longitude:121.4,coordinateSystem:'wgs84',capturedAt:Date.now()/1000,battery:80};
let snapshot = {latest,online:true,battery:80,fixValid:true,desiredMode:'finding',appliedMode:'normal'};
let replies = [];
global.Page = definition => {page=definition;};
global.wx = {
  getStorageSync: () => stored, removeStorageSync: () => {stored=null;}, setStorageSync: (_,value) => {stored=value;},
  request(options) {
    replies.push(options.url);
    assert.equal(options.header.Authorization,'Bearer test-token');
    if (options.url.endsWith('/snapshot')) return options.success({statusCode:200,data:snapshot});
    if (options.url.includes('/track?')) return options.success({statusCode:200,data:{points:[latest],nextCursor:null}});
    throw new Error('unexpected route '+options.url);
  }
};
require('../miniprogram/pages/index/index');
page.data={...page.data,demo:false,loggedIn:true,deviceId:'pet-one',petName:'团团'};
page.setData=values=>Object.assign(page.data,values);page.active=true;
(async()=>{
  await page.refresh();
  assert.equal(page.data.markers.length,1);
  assert.notEqual(page.data.latitude,latest.latitude,'raw WGS84 must be converted');
  assert.equal(page.data.modeText,'等待设备确认');
  snapshot.appliedMode='finding';latest.capturedAt-=200;snapshot.online=false;snapshot.fixValid=false;
  await page.refresh();
  assert(page.data.status.includes('位置已过期'));assert(page.data.status.includes('设备离线'));
  assert.equal(page.data.modeText,'设备已确认寻找模式');
  wx.request=options=>options.success({statusCode:401,data:{detail:'expired'}});
  await page.refresh();
  assert.equal(page.data.loggedIn,false);assert.equal(page.data.markers.length,0);assert.equal(stored,null);
  const {dayRange}=require('../miniprogram/utils/api');
  assert.equal(new Date(dayRange('2026-10-11').start*1000).toISOString(),'2026-10-10T16:00:00.000Z');
  console.log('Authenticated mini program, mode acknowledgement, expiration and day boundaries passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
