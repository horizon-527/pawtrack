-- Commit record before metadata; commit removal before deleting record.
-- On interrupted append, orphan record is ignored. On interrupted ack, no duplicate loss.
local M={}
function M.open(kv,capacity)
    local self={kv=kv,capacity=capacity or 64,meta=kv.get('pt_queue') or {head=0,tail=0,dropped=0}}
    assert(self.meta.head>=0 and self.meta.tail>=self.meta.head and self.meta.tail-self.meta.head<=self.capacity,'queue metadata corrupt')
    function self:save() assert(self.kv.set('pt_queue',self.meta),'queue commit failed') end
    function self:append(point)
        if self.meta.tail-self.meta.head>=self.capacity then self.meta.dropped=self.meta.dropped+1;self:save();return false end
        assert(self.kv.set('pt_q_'..(self.meta.tail%self.capacity),point),'point commit failed')
        self.meta.tail=self.meta.tail+1;self:save();return true
    end
    function self:peek()
        if self.meta.head==self.meta.tail then return nil end
        return assert(self.kv.get('pt_q_'..(self.meta.head%self.capacity)),'queue record missing')
    end
    function self:ack()
        assert(self.meta.head<self.meta.tail,'empty queue')
        local key='pt_q_'..(self.meta.head%self.capacity)
        self.meta.head=self.meta.head+1;self:save();self.kv.del(key)
    end
    return self
end
return M
